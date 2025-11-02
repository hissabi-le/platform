import asyncio
import os

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

try:
    from fastapi.testclient import TestClient
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["RATE_LIMIT_LOGIN_PER_MIN"] = "2"
    from src.main import app
    from src.database import engine, Base
    from src.rate_limit import login_rate_limiter
except Exception as exc:  # pragma: no cover - handled via skip
    pytest.skip(f"Required dependencies not installed: {exc}", allow_module_level=True)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    async def init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(init())
    asyncio.run(login_rate_limiter.reset())


client = TestClient(app)


def test_register_login_refresh_and_rate_limit():
    register_payload = {"email": "user@test.com", "password": "secret12345", "org_name": "Test Org"}
    r = client.post("/auth/register", json=register_payload)
    assert r.status_code == 201
    body = r.json()
    assert "access_token" in body and "refresh_token" in body
    access_token = body["access_token"]
    refresh_token = body["refresh_token"]

    # Successful login returns fresh tokens
    asyncio.run(login_rate_limiter.reset())
    r = client.post("/auth/login", json={"email": register_payload["email"], "password": register_payload["password"]})
    assert r.status_code == 200
    login_body = r.json()
    assert login_body["access_token"] != access_token

    # Refresh token rotates tokens
    r = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    refreshed = r.json()
    assert refreshed["access_token"] != access_token

    # Wrong password triggers 401 and contributes to rate limit
    asyncio.run(login_rate_limiter.reset())
    for _ in range(2):
        r = client.post("/auth/login", json={"email": register_payload["email"], "password": "bad"})
        assert r.status_code == 401
    r = client.post("/auth/login", json={"email": register_payload["email"], "password": "bad2"})
    assert r.status_code == 429

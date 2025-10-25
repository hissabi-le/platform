import asyncio
import os

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

try:
    from fastapi.testclient import TestClient
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    from src.main import app
    from src.database import engine, Base, async_session
    from src.models import Organisation
except Exception as exc:  # pragma: no cover - handled via skip
    pytest.skip(f"Required dependencies not installed: {exc}", allow_module_level=True)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    async def init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with async_session() as session:
            session.add(Organisation(name="org"))
            await session.commit()
    asyncio.run(init())


client = TestClient(app)


def test_register_and_login():
    data = {"email": "user@test.com", "password": "secret123", "org_name": "Test Org"}
    r = client.post("/auth/register", json=data)
    assert r.status_code == 201
    r = client.post("/auth/login", json={"email": data["email"], "password": data["password"]})
    assert r.status_code == 200
    r = client.post("/auth/login", json={"email": data["email"], "password": "wrong"})
    assert r.status_code == 401

import asyncio
import os

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

try:
    from fastapi import FastAPI, Depends
    from fastapi.testclient import TestClient

    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    from src.main import require_plan
    from src.database import engine, Base, async_session
    from src.models import Organisation, Subscription, User
except Exception as exc:  # pragma: no cover - handled via skip
    pytest.skip(f"Required dependencies not installed: {exc}", allow_module_level=True)


async def setup_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        org = Organisation(name="org")
        session.add(org)
        await session.flush()
        session.add(Subscription(org_id=org.id, stripe_subscription_id="sub", plan="core", status="active"))
        user = User(org_id=org.id, email="a@test.com", hashed_password="x", role="user")
        session.add(user)
        await session.commit()


aio_loop = asyncio.get_event_loop()
aio_loop.run_until_complete(setup_data())

app_extra = FastAPI()


@app_extra.get("/protected")
async def protected(user: User = Depends(require_plan("assistant"))):
    return {"ok": True}


client = TestClient(app_extra)


def test_paywall():
    response = client.get("/protected")
    assert response.status_code == 402

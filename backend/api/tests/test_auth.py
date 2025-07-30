import asyncio
import os

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
from api.src.main import app
from api.src.database import engine, Base, async_session
from api.src.models import Organisation


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
    data = {"email": "user@test.com", "password": "secret", "org_id": 1, "role": "user"}
    r = client.post("/auth/register", json=data)
    assert r.status_code == 201
    r = client.post("/auth/login", data={"username": data["email"], "password": data["password"]})
    assert r.status_code == 200
    r = client.post("/auth/login", data={"username": data["email"], "password": "wrong"})
    assert r.status_code == 400

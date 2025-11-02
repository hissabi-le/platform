import asyncio

import pytest
from fastapi.testclient import TestClient

from sqlalchemy import select

from src.cache.idempotency_cache import idempotency_cache
from src.cache.subscription_cache import subscription_cache
from src.config import settings
from src.database import Base, async_session, engine
from src.main import app
from src.models import Organisation, Subscription, Upload, User
from src.security import create_access_token, hash_password
from src.tasks import register_enqueue_handler


pytest.importorskip("sqlalchemy")


async def _init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


asyncio.run(_init_db())


client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_caches(tmp_path):
    original_root = settings.storage_local_root
    settings.storage_local_root = str(tmp_path)
    asyncio.run(subscription_cache.clear())
    asyncio.run(idempotency_cache.clear())

    async def _noop_handler(*args, **kwargs):
        return None

    asyncio.run(register_enqueue_handler(_noop_handler))
    yield
    settings.storage_local_root = original_root


async def _create_user_with_subscription(plan: str = "pro", status: str = "active") -> User:
    async with async_session() as session:
        org = Organisation(name="uploads-org")
        session.add(org)
        await session.flush()
        user = User(
            org_id=org.id,
            email="uploads@test.com",
            hashed_password=hash_password("secret123"),
            role="admin",
        )
        session.add(user)
        session.add(
            Subscription(
                org_id=org.id,
                stripe_subscription_id=f"sub-{org.id}",
                plan=plan,
                status=status,
            )
        )
        await session.commit()
        await subscription_cache.invalidate(org.id)
        return user


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


def test_upload_with_idempotency(monkeypatch):
    user = asyncio.run(_create_user_with_subscription())

    captured = []

    async def _fake_enqueue(upload_id: int, org_id: int, storage_path: str) -> None:
        captured.append((upload_id, org_id, storage_path))

    asyncio.run(register_enqueue_handler(_fake_enqueue))

    files = {"file": ("report.csv", b"a,b\n1,2", "text/csv")}
    headers = _auth_headers(user) | {"Idempotency-Key": "abc123"}

    response = client.post("/uploads", headers=headers, files=files)
    assert response.status_code == 202
    first_payload = response.json()
    assert first_payload["status"] == "pending"
    assert first_payload["id"]
    assert captured and captured[0][0] == first_payload["id"]

    # repeated request should return same payload without adding new queue entry
    response_dupe = client.post("/uploads", headers=headers, files=files)
    assert response_dupe.status_code == 202
    second_payload = response_dupe.json()
    assert second_payload == first_payload
    assert len(captured) == 1

    async def fetch_uploads():
        async with async_session() as session:
            rows = await session.execute(select(Upload))
            return rows.scalars().all()

    uploads = asyncio.run(fetch_uploads())
    assert len(uploads) == 1

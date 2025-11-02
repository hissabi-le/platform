import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.cache.subscription_cache import subscription_cache
from src.config import settings
from src.database import Base, async_session, engine
from src.main import app
from src.models import Document, InventoryItem, InventoryMovement, Subscription, Upload, Organisation, User
from src.security import create_access_token, hash_password
from src.storage import store_file

pytest.importorskip("sqlalchemy")


async def _init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


asyncio.run(_init_db())


client = TestClient(app)


@pytest.fixture(autouse=True)
def _prepare_env(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "storage_local_root", str(tmp_path))
    from src import storage

    monkeypatch.setattr(storage, "_scan_bytes_with_clamav", lambda data: None)
    asyncio.run(subscription_cache.clear())


async def _create_user_with_subscription() -> User:
    async with async_session() as session:
        org = Organisation(name="inventory-org")
        session.add(org)
        await session.flush()
        user = User(
            org_id=org.id,
            email="inventory@test.com",
            hashed_password=hash_password("secret123"),
            role="admin",
        )
        session.add(user)
        session.add(
            Subscription(
                org_id=org.id,
                stripe_subscription_id=f"sub-{org.id}",
                plan="pro",
                status="active",
            )
        )
        await session.commit()
        await subscription_cache.invalidate(org.id)
        return user


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user)}"}


@pytest.mark.asyncio
async def test_inventory_crud_and_extract(tmp_path):
    user = await _create_user_with_subscription()
    headers = _auth_headers(user)

    # Create item via API
    resp_item = client.post(
        "/inventory/items",
        headers=headers,
        json={"name": "Chicken", "unit": "kg"},
    )
    assert resp_item.status_code == 201
    item_id = resp_item.json()["id"]

    # Add manual movement
    resp_move = client.post(
        "/inventory/movements",
        headers=headers,
        json={"item_id": item_id, "qty_delta": 10, "unit_cost": 5.0, "memo": "restock"},
    )
    assert resp_move.status_code == 201

    # Prepare document for extraction
    content = b"Item,Qty,Unit,Amount\nChicken,5,kg,100\n"
    path = store_file(user.org_id, "inventory.csv", content)

    async with async_session() as session:
        upload = Upload(org_id=user.org_id, filename="inventory.csv", status="pending")
        session.add(upload)
        await session.flush()
        doc = Document(
            org_id=user.org_id,
            upload_id=upload.id,
            doc_type="upload",
            filename="inventory.csv",
            content_type="text/csv",
            storage_path=path,
            size_bytes=len(content),
        )
        session.add(doc)
        await session.commit()

    resp_extract = client.post(f"/inventory/extract/{doc.id}", headers=headers)
    assert resp_extract.status_code == 200
    assert resp_extract.json()["created_movements"] >= 1

    summary = client.get("/inventory/summary", headers=headers)
    assert summary.status_code == 200
    data = summary.json()
    assert data
    assert any(row["name"] == "Chicken" for row in data)

    movements = client.get(f"/inventory/items/{item_id}/movements", headers=headers)
    assert movements.status_code == 200
    assert len(movements.json()) >= 2

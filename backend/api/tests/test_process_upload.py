import asyncio
from pathlib import Path

import pytest
from sqlalchemy import select

from src.cache.subscription_cache import subscription_cache
from src.config import settings
from src.database import Base, async_session, engine
from src.models import Document, InventoryMovement, Transaction, Upload, Organisation, Subscription
from src.storage import store_file
from src.tasks.process_upload import _process_upload

pytest.importorskip("sqlalchemy")


async def _init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


asyncio.run(_init_db())


@pytest.fixture(autouse=True)
def _set_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "storage_local_root", str(tmp_path))
    from src import storage

    monkeypatch.setattr(storage, "_scan_bytes_with_clamav", lambda data: None)
    asyncio.run(subscription_cache.clear())


@pytest.mark.asyncio
async def test_process_upload_creates_transactions_and_inventory():
    async with async_session() as session:
        org = Organisation(name="ingest-org")
        session.add(org)
        await session.flush()
        session.add(
            Subscription(
                org_id=org.id,
                stripe_subscription_id=f"sub-{org.id}",
                plan="pro",
                status="active",
            )
        )

        content = b"Account,Amount,Item,Qty,Unit\nSales,1500,,,\nChicken Purchase,-500,Chicken,50,kg\n"
        path = store_file(org.id, "ledger.csv", content, upload_id=None)
        doc = Document(
            org_id=org.id,
            upload_id=None,
            doc_type="upload",
            filename="ledger.csv",
            content_type="text/csv",
            storage_path=path,
            size_bytes=len(content),
        )
        session.add(doc)
        await session.flush()
        upload = Upload(org_id=org.id, filename="ledger.csv", status="pending")
        session.add(upload)
        await session.flush()
        doc.upload_id = upload.id
        await session.commit()

        await _process_upload(upload.id, org.id, path)

        await session.refresh(upload)
        assert upload.status == "done"

        txn_rows = (await session.execute(select(Transaction).where(Transaction.org_id == org.id))).scalars().all()
        inv_rows = (
            await session.execute(select(InventoryMovement).where(InventoryMovement.org_id == org.id))
        ).scalars().all()
        assert len(txn_rows) == 1
        assert len(inv_rows) == 1
        assert inv_rows[0].qty_delta == 50.0

        # running again should not duplicate
        await _process_upload(upload.id, org.id, path)
        txn_rows_after = (
            await session.execute(select(Transaction).where(Transaction.org_id == org.id))
        ).scalars().all()
        assert len(txn_rows_after) == 1

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


class TestAIIngestion:
    """Tests for AI-first document ingestion."""
    
    def test_ai_ingest_skips_without_api_key(self, monkeypatch):
        """Without OPENAI_API_KEY, AI ingestion should return None (fallback)."""
        monkeypatch.setattr(settings, "openai_api_key", None)
        
        from src.tasks.process_upload import _ai_ingest_document
        import pandas as pd
        
        df = pd.DataFrame([{"Description": "Office supplies", "Amount": -50}])
        result = asyncio.run(_ai_ingest_document(df))
        
        # Should return None when no API key (triggers fallback)
        assert result is None
    
    def test_parse_ai_response_valid_format(self):
        """_parse_ai_response should correctly parse chain-of-thought output."""
        from src.tasks.process_upload import _parse_ai_response
        
        content = """ANALYSIS:
Looking at this data, I see a mix of revenue and expense transactions.
Row 1 is clearly a sale based on the positive amount and description.
Row 2 appears to be an office supply purchase.

---TRANSACTIONS---
2024-01-15|Widget sale|150.00|Revenue - Sales|USD|paid|no|||
2024-01-15|Office supplies|47.50|Operating Expenses - Supplies|USD|paid|no|||
2024-01-15|Chicken purchase|200.00|Inventory Purchase|LBP|paid|yes|Chicken|10|kg
"""
        result = _parse_ai_response(content)
        
        assert result is not None
        assert len(result) == 3
        
        # Check first transaction (revenue)
        assert result[0]["description"] == "Widget sale"
        assert result[0]["amount"] == 150.00  # Revenue stays positive
        assert result[0]["category"] == "Revenue - Sales"
        assert result[0]["payment_status"] == "paid"
        assert result[0]["is_inventory"] is False
        
        # Check third transaction (inventory)
        assert result[2]["is_inventory"] is True
        assert result[2]["item_name"] == "Chicken"
        assert result[2]["quantity"] == 10
        assert result[2]["unit"] == "kg"
    
    def test_parse_ai_response_missing_delimiter(self):
        """Should return None if TRANSACTIONS delimiter is missing."""
        from src.tasks.process_upload import _parse_ai_response
        
        content = "Just some text without the expected format"
        result = _parse_ai_response(content)
        
        assert result is None
    
    def test_parse_ai_response_empty_transactions(self):
        """Should return empty list for valid format with no transactions."""
        from src.tasks.process_upload import _parse_ai_response
        
        content = """ANALYSIS:
This document appears to be empty or contain no financial data.

---TRANSACTIONS---
"""
        result = _parse_ai_response(content)
        
        assert result == []
    
    def test_persist_transaction_fallback_uses_category(self):
        """Fallback path should use spreadsheet category when present."""
        from src.tasks.process_upload import _persist_transaction_row
        from unittest.mock import MagicMock
        
        mock_session = MagicMock()
        mock_session.add = MagicMock()
        
        row = {"Amount": 100, "Account": "Sales", "Description": "Widget sale", "Category": "Custom Cat"}
        
        async def run_test():
            return await _persist_transaction_row(
                mock_session, row, org_id=1, upload_id=1
            )
        
        result = asyncio.run(run_test())
        
        assert result is True
        added_txn = mock_session.add.call_args[0][0]
        # Should use spreadsheet category
        assert added_txn.category == "Custom Cat"



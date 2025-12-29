from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from datetime import datetime
from typing import Any, Mapping

import dramatiq
import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from ..database import async_session
from ..excel_cleaner import clean_table, load_table
from ..models import Document, InventoryItem, InventoryMovement, Transaction, Upload
from ..storage import load_file
from ..assistant import OpenAIClient
from ..config import settings

logger = logging.getLogger(__name__)



@dramatiq.actor(max_retries=0)
def process_upload(upload_id: int, org_id: int, storage_path: str) -> None:
    asyncio.run(_process_upload(upload_id, org_id, storage_path))


async def _process_upload(upload_id: int, org_id: int, storage_path: str) -> None:
    async with async_session() as session:
        upload = await session.get(Upload, upload_id)
        if not upload:
            logger.warning("Upload %s not found", upload_id)
            return
        if upload.org_id != org_id:
            logger.warning("Upload %s org mismatch (%s != %s)", upload_id, upload.org_id, org_id)
            return
        if upload.status == "done":
            logger.info("Upload %s already processed", upload_id)
            return

        upload.status = "processing"
        await session.commit()
        await session.refresh(upload)

        document = await session.scalar(
            select(Document).where(Document.upload_id == upload_id, Document.org_id == org_id)
        )

        try:
            raw_bytes = load_file(storage_path)
            suffix = ""
            if document and document.filename:
                suffix = os.path.splitext(document.filename)[1]
            if not suffix:
                suffix = os.path.splitext(storage_path)[1]
            tmp_kwargs: dict[str, Any] = {"delete": False}
            if suffix:
                tmp_kwargs["suffix"] = suffix
            with tempfile.NamedTemporaryFile(**tmp_kwargs) as tmp:
                tmp.write(raw_bytes)
                tmp_path = tmp.name
            try:
                df = load_table(tmp_path)
                
                # Attempt LLM-based processing if API key is available
                llm_client = OpenAIClient() if settings.openai_api_key else None
                rows = None
                
                if llm_client:
                    try:
                        if _is_journal_like(df):
                            # Journal/log documents - use LLM journal parsing
                            logger.info("Upload %s detected as journal-like, using LLM parsing", upload_id)
                            lines = _dataframe_to_lines(df)
                            result = llm_client.parse_journal_lines(lines)
                            rows = result.get("entries", [])
                        elif _is_structured_inventory(df):
                            # Structured inventory/invoice - use LLM mapping
                            logger.info("Upload %s detected as structured inventory, using LLM mapping", upload_id)
                            raw_rows = df.to_dict(orient="records")
                            rows = llm_client.map_rows_to_inventory(raw_rows)
                    except Exception as llm_exc:
                        logger.warning("LLM processing failed for upload %s, falling back to heuristics: %s", upload_id, llm_exc)
                        rows = None
                
                # Fallback to heuristic cleaning if LLM didn't produce rows
                if rows is None:
                    logger.info("Upload %s using heuristic clean_table processing", upload_id)
                    df = clean_table(df)
                    rows = df.to_dict(orient="records")
                    
            finally:
                os.unlink(tmp_path)
        except Exception as exc:  # pragma: no cover - defensive
            await _mark_upload_error(session, upload, f"Failed to parse file: {exc}")
            logger.exception("Failed to parse upload %s", upload_id)
            return


        txn_count = 0
        movement_count = 0
        try:
            # idempotent cleanup
            await session.execute(
                delete(Transaction).where(Transaction.org_id == org_id, Transaction.upload_id == upload_id)
            )
            if document:
                await session.execute(
                    delete(InventoryMovement).where(
                        InventoryMovement.org_id == org_id,
                        InventoryMovement.ref_document_id == document.id,
                    )
                )

            for row in rows:
                if _is_inventory_row(row):
                    movement_created = await _persist_inventory_row(
                        session, row, org_id, document.id if document else None
                    )
                    movement_count += int(movement_created)
                else:
                    txn_created = await _persist_transaction_row(session, row, org_id, upload_id)
                    txn_count += int(txn_created)

            upload.status = "done"
            session.add(upload)
            await session.commit()
            logger.info(
                "Processed upload %s (transactions=%s, movements=%s)",
                upload_id,
                txn_count,
                movement_count,
            )
        except Exception as exc:  # pragma: no cover - defensive
            await session.rollback()
            await _mark_upload_error(session, upload, f"Processing failed: {exc}")
            logger.exception("Processing failed for upload %s", upload_id)


async def _mark_upload_error(session, upload: Upload, message: str) -> None:
    upload.status = "error"
    session.add(upload)
    await session.commit()
    logger.error("Upload %s marked as error: %s", upload.id, message)


def _norm_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_float(value: Any) -> float | None:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        return float(value)
    except Exception:
        return None


def _is_inventory_row(row: Mapping[str, Any]) -> bool:
    qty = _to_float(row.get("Qty") or row.get("Quantity"))
    item = row.get("Item") or row.get("Account") or row.get("Description")
    return qty is not None and _norm_str(item) is not None


async def _persist_inventory_row(
    session,
    row: Mapping[str, Any],
    org_id: int,
    document_id: int | None,
) -> bool:
    qty = _to_float(row.get("Qty") or row.get("Quantity"))
    if qty is None or qty == 0:
        return False
    item_name = _norm_str(row.get("Item") or row.get("Account") or row.get("Description"))
    if not item_name:
        return False
    unit = _norm_str(row.get("Unit")) or "unit"
    sku = _norm_str(row.get("SKU"))
    amount = _to_float(row.get("Amount") or row.get("Total") or row.get("Price"))
    unit_cost = (amount / qty) if amount is not None and qty not in (0, None) else None

    item = await session.scalar(
        select(InventoryItem).where(
            InventoryItem.org_id == org_id,
            InventoryItem.name == item_name,
            InventoryItem.unit == unit,
        )
    )
    if not item:
        item = InventoryItem(org_id=org_id, name=item_name, unit=unit, sku=sku)
        session.add(item)
        await session.flush()

    movement = InventoryMovement(
        org_id=org_id,
        item_id=item.id,
        qty_delta=float(qty),
        unit_cost=unit_cost,
        memo=row.get("Description") or "auto-ingest",
        ref_document_id=document_id,
    )
    session.add(movement)
    return True


def _normalize_metadata(row: Mapping[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            normalized[key] = value
        elif isinstance(value, (pd.Timestamp, datetime)):
            normalized[key] = str(value)
        else:
            normalized[key] = str(value)
    return normalized


async def _persist_transaction_row(
    session,
    row: Mapping[str, Any],
    org_id: int,
    upload_id: int,
) -> bool:
    amount = _to_float(row.get("Amount") or row.get("Debit") or row.get("Credit"))
    if amount is None:
        return False
    account = _norm_str(row.get("Account") or row.get("Description"))
    if not account:
        return False
    category = _norm_str(row.get("Category")) or account
    description = _norm_str(row.get("Description"))
    currency = _norm_str(row.get("Currency")) or "LBP"
    raw_date = row.get("Date")
    txn_date = _parse_date(raw_date)
    
    # Classify account type at insertion time for deterministic analytics
    account_type = _classify_account_type(account, category, amount)

    txn = Transaction(
        org_id=org_id,
        upload_id=upload_id,
        txn_date=txn_date,
        account_code=account[:50],
        category=category[:100],
        amount=float(amount),
        currency=currency,
        description=description,
        account_type=account_type,
        metadata_json=_normalize_metadata(row),
    )
    session.add(txn)
    return True


def _parse_date(value: Any) -> datetime:
    if value is None:
        return datetime.utcnow()
    try:
        ts = pd.to_datetime(value, errors="coerce")
        if pd.isna(ts):
            return datetime.utcnow()
        if isinstance(ts, pd.Timestamp):
            return ts.to_pydatetime()
        return datetime.fromisoformat(str(ts))
    except Exception:
        return datetime.utcnow()


# ------------------- Document Type Detection -------------------

def _is_journal_like(df: pd.DataFrame) -> bool:
    """
    Detect if a DataFrame represents unstructured journal/log entries.
    Journal documents typically have:
    - Few columns (1-3)
    - Text-heavy content
    - No clear numeric amount columns
    """
    if len(df.columns) > 4:
        return False
    
    # Check if it looks like free-text entries
    text_cols = [c for c in df.columns if df[c].dtype == object]
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    
    # Journal-like if mostly text with minimal structure
    if len(text_cols) >= 1 and len(numeric_cols) <= 1:
        # Check if text rows are sentence-like (contain multiple words)
        sample = df[text_cols[0]].dropna().head(10)
        avg_words = sample.apply(lambda x: len(str(x).split())).mean() if len(sample) > 0 else 0
        return avg_words > 3  # Average more than 3 words per cell suggests journal entries
    
    return False


def _is_structured_inventory(df: pd.DataFrame) -> bool:
    """
    Detect if a DataFrame represents structured inventory/invoice data.
    Inventory documents typically have:
    - Item/Product/Description column
    - Quantity column
    - Amount/Price/Cost column
    """
    lower_cols = {c.lower(): c for c in df.columns}
    
    # Check for typical inventory column patterns
    item_cols = {"item", "product", "description", "name", "sku", "article"}
    qty_cols = {"qty", "quantity", "qté", "units", "count"}
    amount_cols = {"amount", "total", "price", "cost", "value", "unit_cost"}
    
    has_item = any(col in lower_cols for col in item_cols)
    has_qty = any(col in lower_cols for col in qty_cols)
    has_amount = any(col in lower_cols for col in amount_cols)
    
    # Structured inventory if it has item + (qty or amount)
    return has_item and (has_qty or has_amount)


def _dataframe_to_lines(df: pd.DataFrame) -> list[str]:
    """
    Convert a DataFrame to a list of text lines for LLM journal parsing.
    Concatenates all text columns into readable lines.
    """
    lines = []
    text_cols = [c for c in df.columns if df[c].dtype == object]
    
    for _, row in df.iterrows():
        parts = []
        for col in text_cols:
            val = row.get(col)
            if pd.notna(val) and str(val).strip():
                parts.append(str(val).strip())
        if parts:
            lines.append(" | ".join(parts))
    
    return lines


# ------------------- Account Type Classification -------------------

# Keyword sets for deterministic classification
_REVENUE_KEYWORDS = {"revenue", "sales", "income", "turnover", "receipt", "sell", "sold"}
_COGS_KEYWORDS = {"cogs", "cost of goods", "cost-of-goods", "inventory cost", "materials"}
_EXPENSE_KEYWORDS = {
    "expense", "operating", "rent", "salary", "salaries", "wage", "utilities",
    "marketing", "advertising", "admin", "general", "depreciation", "tax",
    "electricity", "water", "internet", "fuel", "maintenance", "fees"
}
_ASSET_KEYWORDS = {"cash", "bank", "receivable", "inventory", "asset", "prepaid", "equipment"}
_LIABILITY_KEYWORDS = {"payable", "loan", "debt", "accrued", "credit", "mortgage"}
_EQUITY_KEYWORDS = {"equity", "capital", "retained", "earnings", "dividend", "owner"}


def _classify_account_type(account: str, category: str, amount: float | None = None) -> str:
    """
    Classify a transaction into one of: ASSET, LIABILITY, EQUITY, REVENUE, COGS, EXPENSE.
    Uses deterministic keyword matching for financial data integrity.
    """
    from ..models import AccountType
    
    # Combine account and category for matching
    combined = f"{account} {category}".lower()
    
    def _match(keywords: set[str]) -> bool:
        return any(kw in combined for kw in keywords)
    
    # Check in order of specificity
    if _match(_REVENUE_KEYWORDS):
        return AccountType.REVENUE.value
    if _match(_COGS_KEYWORDS):
        return AccountType.COGS.value
    if _match(_ASSET_KEYWORDS):
        return AccountType.ASSET.value
    if _match(_LIABILITY_KEYWORDS):
        return AccountType.LIABILITY.value
    if _match(_EQUITY_KEYWORDS):
        return AccountType.EQUITY.value
    if _match(_EXPENSE_KEYWORDS):
        return AccountType.EXPENSE.value
    
    # Default based on amount sign if no keywords match
    if amount is not None:
        if amount > 0:
            return AccountType.REVENUE.value
        else:
            return AccountType.EXPENSE.value
    
    return AccountType.EXPENSE.value

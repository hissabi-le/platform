from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import tempfile
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping, Optional

import dramatiq
import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from ..assistant import OpenAIClient
from ..config import settings
from ..database import async_session
from ..excel_cleaner import clean_table, load_table, parse_payment_status
from ..models import Document, InventoryItem, InventoryMovement, Transaction, Upload
from ..storage import load_file

logger = logging.getLogger(__name__)

# ============================================================================
# HISSABI AI DOCUMENT INGESTION SYSTEM
# ============================================================================
# Core principle: Hissabi is a database where ANY financial document can be 
# uploaded - messy Excel sheets, informal notes, multilingual data - and an
# AI will understand it on ingestion and properly store all the data.
#
# The AI must:
# 1. Understand ANY format (messy columns, mixed languages, informal naming)
# 2. Extract ALL meaningful financial data
# 3. Properly categorize for downstream analytics (AR/AP, P&L, Balance Sheet)
# 4. Apply business rules (e.g., assume paid unless specified otherwise)
# ============================================================================

# System prompt with all business rules and chain-of-thought instructions
AI_INGESTION_SYSTEM_PROMPT = """You are Hissabi's AI document ingestion system. Your job is to understand ANY uploaded financial document and extract structured transaction data.

## YOUR CAPABILITIES
- Understand messy, informal, or irregularly formatted spreadsheets
- Work with English, French, Arabic (including Arabizi), and mixed-language documents
- Recognize financial data even when column names are non-standard
- Infer missing information from context

## BUSINESS RULES (IMPORTANT)
1. PAYMENT STATUS: Assume ALL transactions are PAID unless explicitly marked as unpaid/outstanding/due/pending
2. CURRENCY: Default to LBP (Lebanese Pound) unless another currency is specified
3. DATES: Parse any date format; use today's date if unclear
4. AMOUNTS: Positive = income/revenue, Negative = expense/cost
5. CATEGORIES: Assign meaningful accounting categories for analytics

## STANDARD CATEGORIES (use these exact values)
Revenue:
- "Revenue - Sales"
- "Revenue - Services" 
- "Revenue - Other"

Expenses:
- "Cost of Goods Sold"
- "Operating Expenses - Rent"
- "Operating Expenses - Utilities"
- "Operating Expenses - Salaries"
- "Operating Expenses - Supplies"
- "Operating Expenses - Marketing"
- "Operating Expenses - Other"
- "Travel & Entertainment"
- "Professional Fees"
- "Bank Fees & Interest"
- "Tax Expense"

Inventory/Assets:
- "Inventory Purchase"
- "Equipment & Assets"

Other:
- "Owner's Draw"
- "Loan & Debt"
- "Transfer"
- "Uncategorized"

## YOUR TASK
For each row of data, you must:
1. THINK: What kind of transaction is this? (reason through the data)
2. EXTRACT: Pull out the key fields
3. CATEGORIZE: Assign the appropriate category
4. VALIDATE: Check if any information is missing or ambiguous

## OUTPUT FORMAT
Respond with your reasoning first (starting with "ANALYSIS:"), then output a line "---TRANSACTIONS---" followed by one transaction per line in this exact format:

DATE|DESCRIPTION|AMOUNT|CATEGORY|CURRENCY|PAYMENT_STATUS|IS_INVENTORY|ITEM_NAME|QUANTITY|UNIT

Rules for the output:
- DATE: YYYY-MM-DD format
- AMOUNT: Positive number (we'll infer sign from category)
- PAYMENT_STATUS: "paid" or "unpaid"
- IS_INVENTORY: "yes" or "no"
- QUANTITY and UNIT: only if IS_INVENTORY is "yes"
- Use | as delimiter, no quotes
- Empty fields should be blank (just ||)

Example:
ANALYSIS:
Looking at this data, I see sales transactions and some expense payments...
Row 1 appears to be a sale of coffee at $15...

---TRANSACTIONS---
2024-01-15|Coffee sales|15.00|Revenue - Sales|USD|paid|no|||
2024-01-15|Office supplies|47.50|Operating Expenses - Supplies|USD|paid|no|||
2024-01-15|Chicken purchase|200.00|Inventory Purchase|LBP|paid|yes|Chicken|10|kg
"""


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

        # Step 1: Load the raw spreadsheet
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
                # Keep a copy of raw data for AI
                raw_df = df.copy()
            finally:
                os.unlink(tmp_path)
        except Exception as exc:
            await _mark_upload_error(session, upload, f"Failed to parse file: {exc}")
            logger.exception("Failed to parse upload %s", upload_id)
            return

        # Step 2: Try AI-first ingestion
        ai_transactions = await _ai_ingest_document(raw_df)
        
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
            
            # Step 3: Process AI transactions if available, otherwise fall back
            if ai_transactions is not None:
                # AI successfully parsed the document
                logger.info("AI ingested %d transactions from upload %s", len(ai_transactions), upload_id)
                
                for txn_data in ai_transactions:
                    if txn_data.get("is_inventory"):
                        # Inventory movement
                        movement_created = await _persist_ai_inventory(
                            session, txn_data, org_id, document.id if document else None
                        )
                        movement_count += int(movement_created)
                    else:
                        # Regular transaction
                        txn_created = await _persist_ai_transaction(
                            session, txn_data, org_id, upload_id
                        )
                        txn_count += int(txn_created)
            else:
                # Fall back to excel_cleaner
                logger.info("AI ingestion unavailable, falling back to excel_cleaner for upload %s", upload_id)
                df = clean_table(raw_df)
                rows = df.to_dict(orient="records")
                
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


async def _ai_ingest_document(
    df: pd.DataFrame,
) -> Optional[list[dict[str, Any]]]:
    """
    Use OpenAI to understand and extract transactions from a raw spreadsheet.
    
    This is the core of Hissabi's AI-first ingestion:
    1. Sends the raw spreadsheet data to GPT
    2. GPT reasons through each row (chain-of-thought)
    3. GPT outputs structured data in a parseable format
    4. We parse the output ourselves (no JSON from model = less hallucination)
    
    Returns:
        List of transaction dicts if AI succeeds, None if fallback needed.
    """
    if not settings.openai_api_key:
        logger.info("OpenAI API key not set, AI ingestion unavailable")
        return None
    
    llm = OpenAIClient()
    if llm.client is None:
        logger.info("OpenAI client unavailable, AI ingestion unavailable")
        return None
    
    # Convert DataFrame to a readable format for GPT
    # Limit to first 100 rows for token management
    rows_for_ai = df.head(100).to_dict(orient="records")
    
    # Build user prompt with the actual data
    user_prompt = f"""Here is a spreadsheet with {len(df)} rows (showing first {len(rows_for_ai)}):

COLUMN HEADERS: {list(df.columns)}

DATA:
"""
    for idx, row in enumerate(rows_for_ai):
        # Clean up NaN values
        clean_row = {k: ("" if pd.isna(v) else v) for k, v in row.items()}
        user_prompt += f"Row {idx + 1}: {clean_row}\n"
    
    user_prompt += f"""
TOTAL ROWS: {len(df)}

Please analyze this document, understand each transaction, and extract the financial data.
Remember: Assume all transactions are PAID unless explicitly marked otherwise.
Today's date: {datetime.utcnow().strftime('%Y-%m-%d')}
"""
    
    try:
        response = llm.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": AI_INGESTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=4000,
        )
        
        content = response.choices[0].message.content or ""
        
        # Parse the response using chain-of-thought output format
        return _parse_ai_response(content)
        
    except Exception as e:
        logger.warning("AI ingestion failed: %s", e)
        return None


def _parse_ai_response(content: str) -> Optional[list[dict[str, Any]]]:
    """
    Parse the AI's chain-of-thought response into structured transactions.
    
    We parse delimited text instead of asking for JSON because:
    1. Less hallucination - model is better at natural text
    2. More robust - easy to parse simple delimited format
    3. Chain-of-thought reasoning improves accuracy
    """
    if "---TRANSACTIONS---" not in content:
        logger.warning("AI response missing TRANSACTIONS delimiter")
        return None
    
    # Split at the delimiter and get the transactions part
    parts = content.split("---TRANSACTIONS---")
    if len(parts) < 2:
        return None
    
    transactions_text = parts[1].strip()
    if not transactions_text:
        return []
    
    transactions = []
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    for line in transactions_text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        
        # Parse: DATE|DESCRIPTION|AMOUNT|CATEGORY|CURRENCY|PAYMENT_STATUS|IS_INVENTORY|ITEM_NAME|QUANTITY|UNIT
        parts = line.split("|")
        if len(parts) < 6:
            logger.debug("Skipping malformed line: %s", line[:50])
            continue
        
        try:
            date_str = parts[0].strip() or today
            description = parts[1].strip()
            amount_str = parts[2].strip()
            category = parts[3].strip() or "Uncategorized"
            currency = parts[4].strip() or "LBP"
            payment_status = parts[5].strip().lower() or "paid"
            
            # Parse amount
            try:
                amount = float(amount_str.replace(",", "").replace(" ", ""))
            except (ValueError, TypeError):
                logger.debug("Skipping row with invalid amount: %s", amount_str)
                continue
            
            # Skip rows with no meaningful data
            if not description or amount == 0:
                continue
            
            # Parse date
            try:
                txn_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                txn_date = datetime.utcnow()
            
            # Determine if expense (make amount negative for expenses)
            is_expense = any(cat in category for cat in [
                "Expense", "Cost", "Tax", "Fees", "Purchase", "Draw", "Loan", "Debt"
            ])
            if is_expense and amount > 0:
                amount = -amount
            
            txn_data = {
                "date": txn_date,
                "description": description[:255],
                "amount": amount,
                "category": category[:100],
                "currency": currency[:10],
                "payment_status": "paid" if payment_status == "paid" else "unpaid",
                "is_inventory": False,
                "item_name": None,
                "quantity": None,
                "unit": None,
            }
            
            # Check if this is an inventory item
            if len(parts) >= 7:
                is_inventory = parts[6].strip().lower() == "yes"
                if is_inventory:
                    txn_data["is_inventory"] = True
                    txn_data["item_name"] = parts[7].strip() if len(parts) > 7 else description
                    if len(parts) > 8 and parts[8].strip():
                        try:
                            txn_data["quantity"] = float(parts[8].strip())
                        except ValueError:
                            pass
                    if len(parts) > 9:
                        txn_data["unit"] = parts[9].strip() or None
            
            transactions.append(txn_data)
            
        except Exception as e:
            logger.debug("Error parsing AI row: %s - %s", line[:50], e)
            continue
    
    return transactions


async def _persist_ai_transaction(
    session,
    txn_data: dict[str, Any],
    org_id: int,
    upload_id: int,
) -> bool:
    """Persist a transaction from AI ingestion."""
    txn = Transaction(
        org_id=org_id,
        upload_id=upload_id,
        txn_date=txn_data["date"],
        account_code=txn_data["description"][:50],
        category=txn_data["category"],
        amount=float(txn_data["amount"]),
        currency=txn_data["currency"],
        description=txn_data["description"],
        metadata_json={},
        payment_status=txn_data["payment_status"],
    )
    session.add(txn)
    return True


async def _persist_ai_inventory(
    session,
    txn_data: dict[str, Any],
    org_id: int,
    document_id: Optional[int],
) -> bool:
    """Persist an inventory movement from AI ingestion."""
    item_name = txn_data.get("item_name") or txn_data.get("description", "Unknown")
    quantity = txn_data.get("quantity")
    
    if not quantity:
        logger.debug("Skipping inventory without quantity: %s", item_name)
        return False
    
    # Find or create inventory item
    from sqlalchemy import select
    query = select(InventoryItem).where(
        InventoryItem.org_id == org_id,
        InventoryItem.name == item_name[:100],
    )
    result = await session.execute(query)
    item = result.scalar_one_or_none()
    
    if not item:
        item = InventoryItem(
            org_id=org_id,
            name=item_name[:100],
            sku=None,
            default_unit=txn_data.get("unit"),
            reorder_level=0,
            current_qty=0,
            weighted_avg_cost=0,
        )
        session.add(item)
        await session.flush()
    
    # Determine movement direction
    category = txn_data.get("category", "")
    is_purchase = "Purchase" in category or txn_data.get("amount", 0) < 0
    qty_delta = abs(quantity) if is_purchase else -abs(quantity)
    
    movement = InventoryMovement(
        org_id=org_id,
        item_id=item.id,
        movement_type="purchase" if is_purchase else "sale",
        qty_delta=qty_delta,
        unit=txn_data.get("unit"),
        unit_cost=abs(txn_data.get("amount", 0) / quantity) if quantity else None,
        total_cost=abs(txn_data.get("amount", 0)),
        ref_type="upload",
        ref_document_id=document_id,
        movement_date=txn_data.get("date", datetime.utcnow()),
        notes=txn_data.get("description"),
    )
    session.add(movement)
    return True


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
    ai_category: str | None = None,
) -> bool:
    from ..excel_cleaner import parse_payment_status
    
    amount = _to_float(row.get("Amount") or row.get("Debit") or row.get("Credit"))
    if amount is None:
        return False
    account = _norm_str(row.get("Account") or row.get("Description"))
    if not account:
        return False
    # Prefer AI category, then spreadsheet category, then account/description
    category = ai_category or _norm_str(row.get("Category")) or account
    description = _norm_str(row.get("Description"))
    currency = _norm_str(row.get("Currency")) or "LBP"
    raw_date = row.get("Date")
    txn_date = _parse_date(raw_date)
    
    # Extract payment status from PaymentStatus column (defaults to 'paid')
    payment_status = parse_payment_status(row.get("PaymentStatus"))

    txn = Transaction(
        org_id=org_id,
        upload_id=upload_id,
        txn_date=txn_date,
        account_code=account[:50],
        category=category[:100],
        amount=float(amount),
        currency=currency,
        description=description,
        metadata_json=_normalize_metadata(row),
        payment_status=payment_status,
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

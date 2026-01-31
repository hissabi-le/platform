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

# Oracle AI System Prompt - Comprehensive Accounting Intelligence
AI_INGESTION_SYSTEM_PROMPT = """You are a Senior Certified Public Accountant (CPA) with 20+ years of experience in accounting for businesses of all sizes financial analysis, and bookkeeping. You have deep expertise in GAAP, accounts receivable/payable management, and financial statement preparation, and are able to fully understand ANY financial document or information sheet a business might upload.

You are Hissabi's AI Accounting Oracle. You understand ANY financial document a small business might upload. Your job is to thoroughly analyze the document and extract ALL financial data with proper accounting classification.

## YOUR IDENTITY
You are the brain behind a small business accounting platform. The users are entrepreneurs, shop owners, freelancers, and small business owners who may not have formal accounting training. You must be smart enough to understand their messy real-world documents and translate them into proper accounting records.

## DOCUMENT UNDERSTANDING
Before extracting data, ANALYZE the entire document structure:
1. What TYPE of document is this? (Sales log, expense tracker, invoice, bank statement, inventory list, AR/AP aging report, etc.)
2. What TIME PERIOD does it cover? Look for explicit dates, or relative markers like "Month 1", "Week of", "Q1", etc.
3. What SECTIONS exist? (Some spreadsheets have separate areas for income, expenses, receivables, etc.)
4. What CURRENCY is being used? (Look for symbols: $, €, £, ل.ل, or text like USD, LBP, EUR)

## COMPLETE CHART OF ACCOUNTS (use these exact category values)

### ASSETS (Balance Sheet)
- "Cash & Bank"
- "Accounts Receivable" - money owed TO the business
- "Inventory"
- "Prepaid Expenses"
- "Equipment & Assets"
- "Other Current Assets"

### LIABILITIES (Balance Sheet)  
- "Accounts Payable" - money owed BY the business
- "Accrued Expenses"
- "Short-term Loans"
- "Long-term Debt"
- "Other Liabilities"

### REVENUE (P&L - Income)
- "Revenue - Sales" - product sales
- "Revenue - Services" - service income
- "Revenue - Other" - miscellaneous income

### COST OF GOODS SOLD (P&L)
- "Cost of Goods Sold" - direct costs of products sold
- "Inventory Purchase" - buying inventory/stock

### OPERATING EXPENSES (P&L)
- "Operating Expenses - Rent"
- "Operating Expenses - Utilities" (electricity, water, internet)
- "Operating Expenses - Salaries" (wages, payroll)
- "Operating Expenses - Supplies" (office supplies, cleaning)
- "Operating Expenses - Marketing" (ads, promotions)
- "Operating Expenses - Insurance"
- "Operating Expenses - Maintenance"
- "Operating Expenses - Other"

### OTHER EXPENSES (P&L)
- "Travel & Entertainment"
- "Professional Fees" (legal, accounting, consulting)
- "Bank Fees & Interest"
- "Tax Expense"
- "Depreciation"

### EQUITY & OTHER
- "Owner's Draw" - owner withdrawals
- "Owner's Investment" - capital contributions
- "Loan & Debt" - loan transactions
- "Transfer" - internal transfers
- "Uncategorized" - when truly unclear

## PAYMENT STATUS DETECTION (CRITICAL FOR AR/AP)

DO NOT assume everything is paid. Carefully analyze each transaction:

### Mark as UNPAID if you see ANY of these signals:
- Words: "due", "owing", "outstanding", "receivable", "payable", "invoice", "to collect", "to pay", "pending", "credit", "on account", "net 30", "net 60"
- Columns named: "due date", "payment due", "days outstanding", "aging", "balance due"
- Invoice numbers without "paid" indicator
- Aging buckets: "0-30 days", "30-60 days", "60-90 days", "90+ days"
- Arabic/French equivalents: "مستحق", "دين", "à payer", "à recevoir"

### Mark as PAID if you see:
- Words: "paid", "settled", "cleared", "received", "collected", "cash", "completed"
- Payment method noted: "check #", "wire", "credit card", "PayPal"
- Receipt numbers or confirmation codes
- Arabic/French equivalents: "مدفوع", "payé", "réglé"

### DEFAULT LOGIC:
- Bank statement transactions → PAID (already in bank)
- Invoices without status → UNPAID (invoices are requests for payment)
- Sales receipts → PAID (point of sale)
- Bills/expenses without status → assume PAID unless aging report

## AR/AP CLASSIFICATION (CRITICAL)

### Accounts RECEIVABLE (money coming TO business):
- Revenue marked as UNPAID → AR entry
- Keywords: "customer owes", "invoice sent", "to collect", "sales on credit"
- Aging reports showing money owed to you

### Accounts PAYABLE (money going FROM business):
- Expenses marked as UNPAID → AP entry  
- Keywords: "bill due", "supplier invoice", "to pay", "vendor credit"
- Aging reports showing money you owe

## DATE HANDLING

### Absolute dates - parse to YYYY-MM-DD:
- "01/15/2024", "15-01-24", "Jan 15, 2024", "2024-01-15"

### Relative dates - FLAG AS AMBIGUOUS:
- "Month 1", "Week 3", "Q1", "Period 5", "M1", "W/E 15"
- If you see these, set AMBIGUOUS_DATES=yes in metadata

### No dates visible:
- Use today's date but note uncertainty

## LANGUAGE SUPPORT
Understand and normalize from:
- English, French, Arabic, Arabizi (Arabic written in Latin letters)
- Mixed language documents
- Common abbreviations: "inv" = invoice, "pmt" = payment, "rcpt" = receipt
- Arabic accounting terms: مبيعات (sales), مشتريات (purchases), إيرادات (revenue), مصروفات (expenses)

## YOUR ANALYSIS PROCESS

1. **SCAN**: Read the entire document first. Understand its structure.
2. **IDENTIFY**: What type of document? What time period? What sections?
3. **CLASSIFY**: For each row, determine the proper accounting category
4. **DETECT**: Is this paid or unpaid? Is it AR or AP?
5. **EXTRACT**: Pull out all the structured data
6. **FLAG**: Note any ambiguities (dates, categories, amounts)

## OUTPUT FORMAT

Start with your analysis:
```
ANALYSIS:
Document type: [type]
Time period: [explicit dates or "ambiguous - needs user input"]
Currency detected: [currency]
Key observations: [what you noticed]

[Your reasoning for each section/row]
```

Then output metadata line:
```
---METADATA---
AMBIGUOUS_DATES=yes|no
DETECTED_CURRENCY=USD|LBP|EUR|etc
DOCUMENT_TYPE=sales_log|expense_tracker|invoice|bank_statement|inventory|ar_aging|ap_aging|mixed
```

Then output transactions:
```
---TRANSACTIONS---
DATE|DESCRIPTION|AMOUNT|CATEGORY|CURRENCY|PAYMENT_STATUS|IS_AR|IS_AP|ITEM_NAME|QUANTITY|UNIT
```

Field rules:
- DATE: YYYY-MM-DD (or "AMBIGUOUS" if relative dates used)
- AMOUNT: Positive number (category determines if income/expense)
- PAYMENT_STATUS: "paid" or "unpaid" (do NOT default to paid blindly)
- IS_AR: "yes" if this is money owed TO business (unpaid revenue)
- IS_AP: "yes" if this is money owed BY business (unpaid expense)
- Use | delimiter, empty fields = blank

Example output:
---METADATA---
AMBIGUOUS_DATES=no
DETECTED_CURRENCY=USD
DOCUMENT_TYPE=mixed

---TRANSACTIONS---
2024-01-15|Coffee sales to customer ABC|150.00|Revenue - Sales|USD|unpaid|yes|no|||
2024-01-15|Office rent January|1200.00|Operating Expenses - Rent|USD|paid|no|no|||
2024-01-15|Supplier invoice - beans|500.00|Cost of Goods Sold|USD|unpaid|no|yes|||
2024-01-15|Cash register sales|847.50|Revenue - Sales|USD|paid|no|no|||
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
                    # Skip inventory logic - process everything as transactions
                    # if txn_data.get("is_inventory"):
                    #     movement_created = await _persist_ai_inventory(...)
                    #     movement_count += int(movement_created)
                    # else:
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
                    # Skip inventory logic - process everything as transactions
                    # if _is_inventory_row(row):
                    #     movement_created = await _persist_inventory_row(...)
                    #     movement_count += int(movement_created)
                    # else:
                    txn_created = await _persist_transaction_row(session, row, org_id, upload_id)
                    txn_count += int(txn_created)

            upload.status = "done"
            session.add(upload)
            await session.commit()
            
            # Invalidate analytics cache so dashboard shows new data
            try:
                from ..cache.analytics_cache import analytics_cache
                await analytics_cache.clear_org(org_id)
                logger.info("Cleared analytics cache for org %s", org_id)
            except Exception as cache_err:
                logger.warning("Failed to clear analytics cache: %s", cache_err)
            
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
    # Increased limit to 500 rows for better coverage of large documents
    rows_for_ai = df.head(500).to_dict(orient="records")
    
    # Build user prompt with the actual data
    user_prompt = f"""Here is a financial document with {len(df)} rows (showing first {len(rows_for_ai)}):

COLUMN HEADERS: {list(df.columns)}

DATA:
"""
    for idx, row in enumerate(rows_for_ai):
        # Clean up NaN values
        clean_row = {k: ("" if pd.isna(v) else v) for k, v in row.items()}
        user_prompt += f"Row {idx + 1}: {clean_row}\n"
    
    user_prompt += f"""
TOTAL ROWS: {len(df)}

Please thoroughly analyze this document:
1. Identify the document type and structure
2. Detect the time period (flag if dates are ambiguous like "Month 1")
3. Classify each transaction with proper accounting category
4. Detect payment status - DO NOT assume paid unless evidence
5. Identify any AR (receivables) or AP (payables) entries

Today's date: {datetime.utcnow().strftime('%Y-%m-%d')}

CRITICAL INSTRUCTION: You MUST start your response with "ANALYSIS:", then "---METADATA---", then "---TRANSACTIONS---". Do not wrap the output in markdown code blocks.
"""
    
    try:
        # Use o3-mini reasoning model for complex accounting analysis
        response = llm.client.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": AI_INGESTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            # temperature=0.1, # Not supported in o3-mini
            max_completion_tokens=10000,  # Increased for larger documents, renamed for o-series models
        )
        
        content = response.choices[0].message.content or ""
        
        # Parse the response using chain-of-thought output format
        return _parse_ai_response(content)
        
    except Exception as e:
        logger.exception("AI ingestion failed with error: %s", e)
        return None


def _parse_ai_response(content: str) -> Optional[list[dict[str, Any]]]:
    """
    Parse the AI Oracle's response into structured transactions.
    
    New format includes:
    - METADATA section with document info (ambiguous dates, currency, type)
    - TRANSACTIONS section with AR/AP classification
    
    Returns:
        List of transaction dicts with proper AR/AP flags and payment status.
    """
    if "---TRANSACTIONS---" not in content:
        logger.warning("AI response missing TRANSACTIONS delimiter. Raw content start: %s", content[:1000])
        return None
    
    # Parse metadata section if present
    metadata = {
        "ambiguous_dates": False,
        "detected_currency": "LBP",
        "document_type": "mixed",
    }
    
    if "---METADATA---" in content:
        metadata_section = content.split("---METADATA---")[1].split("---TRANSACTIONS---")[0]
        for line in metadata_section.strip().split("\n"):
            line = line.strip()
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip().lower()
                value = value.strip().lower()
                if "ambiguous" in key:
                    metadata["ambiguous_dates"] = value == "yes"
                elif "currency" in key:
                    metadata["detected_currency"] = value.upper()
                elif "type" in key:
                    metadata["document_type"] = value
    
    # Log metadata for debugging
    logger.info("AI Metadata: %s", metadata)
    
    # Split at the transactions delimiter
    transactions_text = content.split("---TRANSACTIONS---")[1].strip()
    if not transactions_text:
        return []
    
    transactions = []
    today = datetime.utcnow().strftime("%Y-%m-%d")
    default_currency = metadata.get("detected_currency", "LBP")
    
    for line in transactions_text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("```"):
            continue
        
        # New format: DATE|DESCRIPTION|AMOUNT|CATEGORY|CURRENCY|PAYMENT_STATUS|IS_AR|IS_AP|ITEM_NAME|QUANTITY|UNIT
        parts = line.split("|")
        if len(parts) < 6:
            logger.debug("Skipping malformed line: %s", line[:50])
            continue
        
        try:
            date_str = parts[0].strip() or today
            description = parts[1].strip()
            amount_str = parts[2].strip()
            category = parts[3].strip() or "Uncategorized"
            currency = parts[4].strip() or default_currency
            payment_status = parts[5].strip().lower() or "paid"
            
            # Parse IS_AR and IS_AP (new fields)
            is_ar = False
            is_ap = False
            if len(parts) >= 7:
                is_ar = parts[6].strip().lower() == "yes"
            if len(parts) >= 8:
                is_ap = parts[7].strip().lower() == "yes"
            
            # Parse amount
            try:
                amount = float(amount_str.replace(",", "").replace(" ", ""))
            except (ValueError, TypeError):
                logger.debug("Skipping row with invalid amount: %s", amount_str)
                continue
            
            # Skip rows with no meaningful data
            if not description or amount == 0:
                continue
            
            # Parse date - handle AMBIGUOUS marker
            if date_str.upper() == "AMBIGUOUS":
                txn_date = datetime.utcnow()
            else:
                try:
                    txn_date = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    txn_date = datetime.utcnow()
            
            # Determine if expense (make amount negative for expenses)
            is_expense = any(cat in category for cat in [
                "Expense", "Cost", "Tax", "Fees", "Purchase", "Draw", "Loan", "Debt", 
                "Payable", "Depreciation", "Interest"
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
                "is_ar": is_ar,  # Accounts Receivable (money owed TO business)
                "is_ap": is_ap,  # Accounts Payable (money owed BY business)
                "is_inventory": False,
                "item_name": None,
                "quantity": None,
                "unit": None,
                "ambiguous_date": metadata.get("ambiguous_dates", False),
            }
            
            # Parse inventory fields if present (positions 8, 9, 10)
            if len(parts) >= 9 and parts[8].strip():
                txn_data["item_name"] = parts[8].strip()
            if len(parts) >= 10 and parts[9].strip():
                try:
                    txn_data["quantity"] = float(parts[9].strip())
                    txn_data["is_inventory"] = True
                except ValueError:
                    pass
            if len(parts) >= 11:
                txn_data["unit"] = parts[10].strip() or None
            
            transactions.append(txn_data)
            
        except Exception as e:
            logger.debug("Error parsing AI row: %s - %s", line[:50], e)
            continue
    
    logger.info("Parsed %d transactions from AI response", len(transactions))
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
        if pd.isna(value):  # Handles NaN, None, NaT
            normalized[key] = None
        elif isinstance(value, (int, float, bool)):
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

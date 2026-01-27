from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..balance_sheet import generate_pnl
from ..cache.analytics_cache import analytics_cache
from ..database import get_db
from ..repositories.transaction import TransactionRepo
from ..security import AuthContext, require_plan

router = APIRouter(prefix="/analytics", tags=["analytics"])

_RANGES: dict[str, timedelta] = {
    "1m": timedelta(days=30),
    "3m": timedelta(days=90),
    "6m": timedelta(days=180),
    "1y": timedelta(days=365),
}


@router.get("/pnl", response_model=dict)
async def analytics_pnl(
    range: Literal["1y", "6m", "3m", "1m"] = "3m",
    auth: AuthContext = Depends(require_plan("analytics_basic")),
    session: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    window = _RANGES[range]
    start = now - window

    cached = await analytics_cache.get_pnl(auth.user.org_id, range)
    if cached:
        return cached

    trepo = TransactionRepo()
    tx = await trepo.window(session, auth.user.org_id, start, now)
    rows = [
        {
            "Account": t.account_code,
            "Category": t.category,
            "Amount": t.amount,
            "Date": t.txn_date,
            "Description": t.description,
        }
        for t in tx
    ]
    pnl = generate_pnl(rows)
    expenses_total = pnl["cogs"] + pnl["total_expenses"]

    series_map: dict[tuple[int, int], dict[str, float | str]] = {}
    for t in tx:
        period_key = (t.txn_date.year, t.txn_date.month)
        entry = series_map.setdefault(
            period_key,
            {
                "date": datetime(t.txn_date.year, t.txn_date.month, 1).date().isoformat(),
                "revenue": 0.0,
                "expenses": 0.0,
            },
        )
        amount = float(t.amount) if t.amount else 0.0
        if amount >= 0:
            entry["revenue"] = float(entry["revenue"]) + amount
        else:
            entry["expenses"] = float(entry["expenses"]) + abs(amount)

    series = [series_map[key] for key in sorted(series_map.keys())]

    result = {
        "range": range,
        "revenue": pnl["revenue"],
        "expenses": expenses_total,
        "profit": pnl["net_income"],
        "series": series,
    }
    await analytics_cache.set_pnl(auth.user.org_id, range, result)
    return result


@router.get("/receivables", response_model=dict)
async def analytics_receivables(
    auth: AuthContext = Depends(require_plan("analytics_basic")),
    session: AsyncSession = Depends(get_db),
):
    """Get accounts receivable summary - unpaid revenue entries (money owed TO user)."""
    from sqlalchemy import select, func
    from ..models import JournalEntry, Transaction
    
    # Get unpaid revenue from journal entries
    journal_query = select(
        JournalEntry.category,
        func.sum(JournalEntry.total).label("total"),
        func.count(JournalEntry.id).label("count"),
    ).where(
        JournalEntry.org_id == auth.user.org_id,
        JournalEntry.payment_status == "unpaid",
        JournalEntry.entry_type == "revenue",
    ).group_by(JournalEntry.category)
    
    journal_result = await session.execute(journal_query)
    journal_rows = journal_result.all()
    
    # Get unpaid revenue from transactions (positive amounts = revenue)
    txn_query = select(
        Transaction.category,
        func.sum(Transaction.amount).label("total"),
        func.count(Transaction.id).label("count"),
    ).where(
        Transaction.org_id == auth.user.org_id,
        Transaction.payment_status == "unpaid",
        Transaction.amount > 0,
    ).group_by(Transaction.category)
    
    txn_result = await session.execute(txn_query)
    txn_rows = txn_result.all()
    
    # Combine results
    by_category: dict[str, dict] = {}
    total_receivable = 0.0
    total_count = 0
    
    for row in journal_rows:
        cat = row.category or "Uncategorized"
        amount = float(row.total or 0)
        by_category[cat] = {"amount": amount, "count": row.count}
        total_receivable += amount
        total_count += row.count
    
    for row in txn_rows:
        cat = row.category or "Uncategorized"
        amount = float(row.total or 0)
        if cat in by_category:
            by_category[cat]["amount"] += amount
            by_category[cat]["count"] += row.count
        else:
            by_category[cat] = {"amount": amount, "count": row.count}
        total_receivable += amount
        total_count += row.count
    
    breakdown = [
        {"category": k, "amount": v["amount"], "count": v["count"]}
        for k, v in sorted(by_category.items(), key=lambda x: -x[1]["amount"])
    ]
    
    return {
        "total": total_receivable,
        "count": total_count,
        "breakdown": breakdown,
    }


@router.get("/payables", response_model=dict)
async def analytics_payables(
    auth: AuthContext = Depends(require_plan("analytics_basic")),
    session: AsyncSession = Depends(get_db),
):
    """Get accounts payable summary - unpaid expense entries (money owed BY user)."""
    from sqlalchemy import select, func
    from ..models import JournalEntry, Transaction
    
    # Get unpaid expenses from journal entries (cost type)
    journal_query = select(
        JournalEntry.category,
        func.sum(JournalEntry.total).label("total"),
        func.count(JournalEntry.id).label("count"),
    ).where(
        JournalEntry.org_id == auth.user.org_id,
        JournalEntry.payment_status == "unpaid",
        JournalEntry.entry_type.in_(["cost", "inventory_purchase"]),
    ).group_by(JournalEntry.category)
    
    journal_result = await session.execute(journal_query)
    journal_rows = journal_result.all()
    
    # Get unpaid expenses from transactions (negative amounts = expenses)
    txn_query = select(
        Transaction.category,
        func.sum(func.abs(Transaction.amount)).label("total"),
        func.count(Transaction.id).label("count"),
    ).where(
        Transaction.org_id == auth.user.org_id,
        Transaction.payment_status == "unpaid",
        Transaction.amount < 0,
    ).group_by(Transaction.category)
    
    txn_result = await session.execute(txn_query)
    txn_rows = txn_result.all()
    
    # Combine results
    by_category: dict[str, dict] = {}
    total_payable = 0.0
    total_count = 0
    
    for row in journal_rows:
        cat = row.category or "Uncategorized"
        amount = float(row.total or 0)
        by_category[cat] = {"amount": amount, "count": row.count}
        total_payable += amount
        total_count += row.count
    
    for row in txn_rows:
        cat = row.category or "Uncategorized"
        amount = float(row.total or 0)
        if cat in by_category:
            by_category[cat]["amount"] += amount
            by_category[cat]["count"] += row.count
        else:
            by_category[cat] = {"amount": amount, "count": row.count}
        total_payable += amount
        total_count += row.count
    
    breakdown = [
        {"category": k, "amount": v["amount"], "count": v["count"]}
        for k, v in sorted(by_category.items(), key=lambda x: -x[1]["amount"])
    ]
    
    return {
        "total": total_payable,
        "count": total_count,
        "breakdown": breakdown,
    }


@router.get("/receivables/list", response_model=list)
async def list_receivables(
    auth: AuthContext = Depends(require_plan("analytics_basic")),
    session: AsyncSession = Depends(get_db),
):
    """List individual unpaid revenue transactions for drill-down view."""
    from sqlalchemy import select, union_all
    from ..models import JournalEntry, JournalDay, Transaction
    
    # Get unpaid revenue from journal entries
    journal_query = (
        select(
            JournalEntry.id.label("id"),
            JournalEntry.item_name.label("description"),
            JournalEntry.total.label("amount"),
            JournalEntry.category,
            JournalEntry.created_at.label("date"),
            JournalEntry.payment_status,
        )
        .select_from(JournalEntry)
        .where(
            JournalEntry.org_id == auth.user.org_id,
            JournalEntry.payment_status == "unpaid",
            JournalEntry.entry_type == "revenue",
        )
    )
    
    journal_result = await session.execute(journal_query)
    
    # Get unpaid revenue from transactions
    txn_query = select(
        Transaction.id,
        Transaction.description,
        Transaction.amount,
        Transaction.category,
        Transaction.txn_date.label("date"),
        Transaction.payment_status,
    ).where(
        Transaction.org_id == auth.user.org_id,
        Transaction.payment_status == "unpaid",
        Transaction.amount > 0,
    )
    
    txn_result = await session.execute(txn_query)
    
    items = []
    for row in journal_result.all():
        items.append({
            "id": row.id,
            "type": "journal",
            "description": row.description or "Unnamed",
            "amount": float(row.amount or 0),
            "category": row.category or "Uncategorized",
            "date": row.date.isoformat() if row.date else None,
        })
    
    for row in txn_result.all():
        items.append({
            "id": row.id,
            "type": "transaction",
            "description": row.description or "Unnamed",
            "amount": float(row.amount or 0),
            "category": row.category or "Uncategorized",
            "date": row.date.isoformat() if row.date else None,
        })
    
    return sorted(items, key=lambda x: x["amount"], reverse=True)


@router.get("/payables/list", response_model=list)
async def list_payables(
    auth: AuthContext = Depends(require_plan("analytics_basic")),
    session: AsyncSession = Depends(get_db),
):
    """List individual unpaid expense transactions for drill-down view."""
    from sqlalchemy import select, func
    from ..models import JournalEntry, Transaction
    
    # Get unpaid expenses from journal entries
    journal_query = select(
        JournalEntry.id,
        JournalEntry.item_name.label("description"),
        JournalEntry.total.label("amount"),
        JournalEntry.category,
        JournalEntry.created_at.label("date"),
    ).where(
        JournalEntry.org_id == auth.user.org_id,
        JournalEntry.payment_status == "unpaid",
        JournalEntry.entry_type.in_(["cost", "inventory_purchase"]),
    )
    
    journal_result = await session.execute(journal_query)
    
    # Get unpaid expenses from transactions
    txn_query = select(
        Transaction.id,
        Transaction.description,
        func.abs(Transaction.amount).label("amount"),
        Transaction.category,
        Transaction.txn_date.label("date"),
    ).where(
        Transaction.org_id == auth.user.org_id,
        Transaction.payment_status == "unpaid",
        Transaction.amount < 0,
    )
    
    txn_result = await session.execute(txn_query)
    
    items = []
    for row in journal_result.all():
        items.append({
            "id": row.id,
            "type": "journal",
            "description": row.description or "Unnamed",
            "amount": float(row.amount or 0),
            "category": row.category or "Uncategorized",
            "date": row.date.isoformat() if row.date else None,
        })
    
    for row in txn_result.all():
        items.append({
            "id": row.id,
            "type": "transaction",
            "description": row.description or "Unnamed",
            "amount": float(row.amount or 0),
            "category": row.category or "Uncategorized",
            "date": row.date.isoformat() if row.date else None,
        })
    
    return sorted(items, key=lambda x: x["amount"], reverse=True)


@router.patch("/transaction/{txn_id}/payment-status")
async def toggle_transaction_payment_status(
    txn_id: int,
    status: str,  # "paid" | "unpaid"
    auth: AuthContext = Depends(require_plan("analytics_basic")),
    session: AsyncSession = Depends(get_db),
):
    """Toggle payment status for a transaction (from Excel uploads). Used for AR/AP tracking."""
    from sqlalchemy import select
    from datetime import datetime
    from ..models import Transaction
    
    if status not in ("paid", "unpaid"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="status must be 'paid' or 'unpaid'")
    
    # Verify transaction exists and belongs to user's org
    query = select(Transaction).where(
        Transaction.id == txn_id,
        Transaction.org_id == auth.user.org_id,
    )
    result = await session.execute(query)
    txn = result.scalar_one_or_none()
    
    if not txn:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Update payment status
    payment_date = datetime.utcnow() if status == "paid" else None
    txn.payment_status = status
    txn.payment_date = payment_date
    
    await session.commit()
    
    return {
        "id": txn.id,
        "payment_status": status,
        "payment_date": payment_date.isoformat() if payment_date else None,
    }

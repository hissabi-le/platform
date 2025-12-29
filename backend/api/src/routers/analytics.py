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
        amount = float(t.amount or 0.0)
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

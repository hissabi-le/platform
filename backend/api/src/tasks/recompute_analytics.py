from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import dramatiq

from ..balance_sheet import generate_pnl
from ..cache.analytics_cache import analytics_cache
from ..database import async_session
from ..repositories.transaction import TransactionRepo

_RANGES: dict[str, timedelta] = {
    "1m": timedelta(days=30),
    "3m": timedelta(days=90),
    "6m": timedelta(days=180),
    "1y": timedelta(days=365),
}


@dramatiq.actor(max_retries=0)
def recompute_analytics(org_id: int) -> None:
    asyncio.run(_recompute(org_id))


async def _recompute(org_id: int) -> None:
    async with async_session() as session:
        repo = TransactionRepo()
        now = datetime.utcnow()
        for range_key, delta in _RANGES.items():
            start = now - delta
            tx = await repo.window(session, org_id, start, now)
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

            series_map: dict[tuple[int, int, int], dict[str, float | str]] = {}
            for t in tx:
                key = (t.txn_date.year, t.txn_date.month, t.txn_date.day)
                entry = series_map.setdefault(
                    key,
                    {
                        "date": t.txn_date.isoformat(),
                        "revenue": 0.0,
                        "expenses": 0.0,
                    },
                )
                amount = t.amount or 0.0
                if amount >= 0:
                    entry["revenue"] = float(entry["revenue"]) + amount
                else:
                    entry["expenses"] = float(entry["expenses"]) + abs(amount)

            payload = {
                "range": range_key,
                "revenue": pnl["revenue"],
                "expenses": expenses_total,
                "profit": pnl["net_income"],
                "series": [series_map[key] for key in sorted(series_map.keys())],
            }
            await analytics_cache.set_pnl(org_id, range_key, payload)

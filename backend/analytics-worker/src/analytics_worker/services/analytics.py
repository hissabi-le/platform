from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Mapping, Sequence

from ..cache import DistributedLock, analytics_cache, job_store
from ..config import settings
from ..repositories.transactions import TransactionRow, window_iter

logger = logging.getLogger(__name__)


PNL_REVENUE_KEYS = {"revenue", "sales", "income", "turnover", "receipt"}
PNL_COGS_KEYS = {"cogs", "cost of goods", "cost-of-goods", "inventory cost"}
PNL_EXPENSE_KEYS = {
    "expense",
    "operating",
    "rent",
    "salary",
    "salaries",
    "wage",
    "utilities",
    "marketing",
    "advertising",
    "admin",
    "general",
    "depreciation",
    "tax",
}


def _classify_pnl_bucket(name: str, default: str, category: str | None = None) -> str:
    lower = name.lower()
    cat_lower = (category or "").lower()

    def _match(keys: set[str]) -> bool:
        return any(key in lower for key in keys) or any(key in cat_lower for key in keys)

    if _match(PNL_REVENUE_KEYS):
        return "revenue"
    if _match(PNL_COGS_KEYS):
        return "cogs"
    if _match(PNL_EXPENSE_KEYS):
        return "expense"
    return default


@dataclass
class SeriesPoint:
    date: str
    revenue: float = 0.0
    expenses: float = 0.0


class PnLAggregator:
    def __init__(self) -> None:
        self._series: Dict[tuple[int, int], SeriesPoint] = {}
        self.rows_processed = 0
        self.revenue_total = 0.0
        self.cogs_total = 0.0
        self.expenses: Dict[str, float] = defaultdict(float)
        self.first_txn: datetime | None = None
        self.latest_txn: datetime | None = None

    def consume(self, row: TransactionRow) -> None:
        self.rows_processed += 1
        self.first_txn = row.txn_date if self.first_txn is None else min(self.first_txn, row.txn_date)
        self.latest_txn = row.txn_date if self.latest_txn is None else max(self.latest_txn, row.txn_date)

        amount = row.amount
        if amount == 0:
            return
        default_bucket = "revenue" if amount >= 0 else "expense"
        bucket = _classify_pnl_bucket(row.account_code or row.category, default_bucket, row.category)
        if bucket == "revenue":
            self.revenue_total += amount
        elif bucket == "cogs":
            self.cogs_total += abs(amount)
        else:
            key = row.category or row.account_code
            self.expenses[key] += abs(amount)

        month_key = (row.txn_date.year, row.txn_date.month)
        entry = self._series.get(month_key)
        if not entry:
            entry = SeriesPoint(date=datetime(row.txn_date.year, row.txn_date.month, 1).date().isoformat())
            self._series[month_key] = entry
        if amount >= 0:
            entry.revenue += amount
        else:
            entry.expenses += abs(amount)

    def snapshot(self) -> dict:
        gross_profit = self.revenue_total - self.cogs_total
        total_expenses = sum(self.expenses.values())
        net_income = gross_profit - total_expenses
        return {
            "revenue": self.revenue_total,
            "cogs": self.cogs_total,
            "gross_profit": gross_profit,
            "expenses": dict(self.expenses),
            "total_expenses": total_expenses,
            "net_income": net_income,
        }

    def series_payload(self) -> List[dict]:
        return [
            {"date": point.date, "revenue": point.revenue, "expenses": point.expenses}
            for _, point in sorted(self._series.items())
        ]


def compute_roi(pnl: Mapping[str, float]) -> dict:
    revenue = float(pnl.get("revenue", 0.0) or 0.0)
    cogs = float(pnl.get("cogs", 0.0) or 0.0)
    total_expenses = float(pnl.get("total_expenses", 0.0) or 0.0)
    net_income = float(pnl.get("net_income", revenue - cogs - total_expenses))
    investment = cogs + total_expenses
    roi_value = net_income / investment if investment > 0 else None
    return {
        "net_income": net_income,
        "total_investment": investment,
        "roi": roi_value,
    }


class AnalyticsService:
    def __init__(self, cache=analytics_cache) -> None:
        self.cache = cache

    async def recompute_org(
        self,
        session,
        org_id: int,
        *,
        ranges: Sequence[str] | None = None,
    ) -> dict[str, dict]:
        range_keys = list(ranges) if ranges else list(settings.analytics_range_windows.keys())
        now = datetime.utcnow()
        payloads: dict[str, dict] = {}
        for range_key in range_keys:
            window_days = settings.analytics_range_windows.get(range_key)
            if not window_days:
                logger.warning("Range %s not configured; skipping", range_key)
                continue
            payload = await self._recompute_range(session, org_id, range_key, now, window_days)
            payloads[range_key] = payload
            await self.cache.set(org_id, range_key, payload)
        return payloads

    async def _recompute_range(
        self,
        session,
        org_id: int,
        range_key: str,
        now: datetime,
        window_days: int,
    ) -> dict:
        start = now - timedelta(days=window_days)
        aggregator = PnLAggregator()
        async for batch in window_iter(
            session,
            org_id,
            start,
            now,
            batch_size=settings.analytics_query_batch_size,
        ):
            for row in batch:
                aggregator.consume(row)

        pnl = aggregator.snapshot()
        roi = compute_roi(pnl)
        response = {
            "range": range_key,
            "as_of": now.isoformat(),
            "revenue": pnl["revenue"],
            "expenses": pnl["total_expenses"],
            "profit": pnl["net_income"],
            "series": aggregator.series_payload(),
            "pnl": pnl,
            "roi": roi,
            "metadata": {
                "rows_processed": aggregator.rows_processed,
                "window_days": window_days,
                "first_txn_at": aggregator.first_txn.isoformat() if aggregator.first_txn else None,
                "latest_txn_at": aggregator.latest_txn.isoformat() if aggregator.latest_txn else None,
            },
        }
        return response

    async def recompute_with_lock(
        self,
        session,
        org_id: int,
        *,
        ranges: Sequence[str] | None = None,
    ) -> dict[str, dict]:
        lock = DistributedLock(f"org-{org_id}", ttl_seconds=settings.analytics_cache_ttl_seconds)
        async with lock.acquire() as acquired:
            if not acquired:
                logger.info("Analytics refresh for org %s already running", org_id)
                return {}
            return await self.recompute_org(session, org_id, ranges=ranges)


async def run_job(
    session,
    org_id: int,
    *,
    ranges: Sequence[str] | None = None,
    reason: str | None = None,
) -> dict[str, dict]:
    """
    Execute an analytics recomputation job with distributed locking + job store tracking.
    """
    service = AnalyticsService()
    lock = DistributedLock(f"org-{org_id}", ttl_seconds=settings.analytics_cache_ttl_seconds)
    job_id = f"analytics-{org_id}-{int(datetime.utcnow().timestamp())}"
    await job_store.start(
        job_id,
        {
            "org_id": org_id,
            "ranges": list(ranges) if ranges else list(settings.analytics_range_windows.keys()),
            "reason": reason,
            "started_at": datetime.utcnow().isoformat(),
        },
    )
    async with lock.acquire() as acquired:
        if not acquired:
            logger.info("Skip analytics job %s – lock busy", job_id)
            await job_store.fail(job_id, {"org_id": org_id, "error": "lock-busy"})
            return {}
        try:
            payload = await service.recompute_org(session, org_id, ranges=ranges)
            await job_store.complete(
                job_id,
                {"org_id": org_id, "finished_at": datetime.utcnow().isoformat(), "summary": payload},
            )
            return payload
        except Exception as exc:
            logger.exception("Analytics recompute failed for org %s", org_id)
            await job_store.fail(
                job_id,
                {
                    "org_id": org_id,
                    "finished_at": datetime.utcnow().isoformat(),
                    "error": str(exc),
                },
            )
            raise

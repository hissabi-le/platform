from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from analytics_worker.repositories.transactions import (
    TransactionRow,
    metadata as tx_metadata,
    transactions_table,
)
from analytics_worker.services.analytics import AnalyticsService, PnLAggregator, compute_roi


def test_pnl_aggregator_and_roi():
    aggregator = PnLAggregator()
    base = datetime(2024, 1, 15)
    aggregator.consume(
        TransactionRow(
            txn_date=base,
            account_code="Sales",
            category="Revenue",
            amount=1200.0,
            description="invoice",
        )
    )
    aggregator.consume(
        TransactionRow(
            txn_date=base + timedelta(days=10),
            account_code="Rent",
            category="Expense",
            amount=-400.0,
            description="rent",
        )
    )
    pnl = aggregator.snapshot()
    assert pnl["revenue"] == 1200.0
    assert pnl["total_expenses"] == 400.0
    series = aggregator.series_payload()
    assert len(series) == 1
    assert series[0]["revenue"] == 1200.0
    assert series[0]["expenses"] == 400.0
    roi = compute_roi(pnl)
    assert pytest.approx(roi["roi"], rel=1e-6) == (800.0 / 400.0)


@pytest.mark.asyncio
async def test_recompute_range_with_sqlite():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(tx_metadata.create_all)

    async with async_session() as session:
        await session.execute(
            transactions_table.insert(),
            [
                {
                    "id": 1,
                    "org_id": 1,
                    "txn_date": datetime(2024, 1, 5),
                    "account_code": "Sales",
                    "category": "Revenue",
                    "amount": 1000.0,
                    "description": "sale",
                },
                {
                    "id": 2,
                    "org_id": 1,
                    "txn_date": datetime(2024, 1, 10),
                    "account_code": "COGS",
                    "category": "COGS",
                    "amount": -200.0,
                    "description": "cogs",
                },
                {
                    "id": 3,
                    "org_id": 1,
                    "txn_date": datetime(2024, 1, 20),
                    "account_code": "Rent Expense",
                    "category": "Expense",
                    "amount": -300.0,
                    "description": "rent",
                },
            ],
        )
        await session.commit()

        service = AnalyticsService()
        payload = await service._recompute_range(
            session,
            org_id=1,
            range_key="custom",
            now=datetime(2024, 2, 1),
            window_days=45,
        )

    assert payload["revenue"] == 1000.0
    assert payload["profit"] == 500.0
    assert payload["expenses"] == 500.0
    assert payload["pnl"]["cogs"] == 200.0
    assert payload["metadata"]["rows_processed"] == 3
    assert len(payload["series"]) == 1

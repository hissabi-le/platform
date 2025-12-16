from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import AsyncIterator, List

from sqlalchemy import Column, DateTime, Integer, MetaData, Numeric, String, Table, Text, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

metadata = MetaData()


transactions_table = Table(
    "transactions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("org_id", Integer, nullable=False, index=True),
    Column("txn_date", DateTime(timezone=True), nullable=False, index=True),
    Column("account_code", String(50), nullable=False),
    Column("category", String(100), nullable=False),
    Column("amount", Numeric(18, 4), nullable=False),
    Column("description", Text),
)


@dataclass(frozen=True)
class TransactionRow:
    txn_date: datetime
    account_code: str
    category: str
    amount: float
    description: str | None

    @classmethod
    def from_record(cls, record) -> "TransactionRow":
        amount = record.amount
        if isinstance(amount, Decimal):
            amount = float(amount)
        return cls(
            txn_date=record.txn_date,
            account_code=record.account_code or "",
            category=record.category or "",
            amount=float(amount),
            description=record.description,
        )


async def window_iter(
    session: AsyncSession,
    org_id: int,
    start: datetime,
    end: datetime,
    *,
    batch_size: int = 2000,
) -> AsyncIterator[List[TransactionRow]]:
    """
    Yield transaction rows ordered by txn_date/primary key to avoid large memory spikes.
    """
    cursor_date: datetime | None = None
    cursor_id: int | None = None
    base_stmt = (
        select(
            transactions_table.c.id,
            transactions_table.c.txn_date,
            transactions_table.c.account_code,
            transactions_table.c.category,
            transactions_table.c.amount,
            transactions_table.c.description,
        )
        .where(
            transactions_table.c.org_id == org_id,
            transactions_table.c.txn_date >= start,
            transactions_table.c.txn_date < end,
        )
        .order_by(transactions_table.c.txn_date.asc(), transactions_table.c.id.asc())
        .limit(batch_size)
    )

    while True:
        stmt = base_stmt
        if cursor_date is not None and cursor_id is not None:
            stmt = stmt.where(
                or_(
                    transactions_table.c.txn_date > cursor_date,
                    and_(
                        transactions_table.c.txn_date == cursor_date,
                        transactions_table.c.id > cursor_id,
                    ),
                )
            )
        result = await session.execute(stmt)
        rows = result.fetchall()
        if not rows:
            break
        records = [TransactionRow.from_record(row) for row in rows]
        cursor_date = rows[-1].txn_date
        cursor_id = rows[-1].id
        yield records
        if len(rows) < batch_size:
            break


__all__ = ["TransactionRow", "transactions_table", "metadata", "window_iter"]

from __future__ import annotations

from typing import AsyncIterator, List

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, select
from sqlalchemy.ext.asyncio import AsyncSession

metadata = MetaData()

organisations_table = Table(
    "organisations",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(255)),
    Column("created_at", DateTime(timezone=True)),
)


async def iter_org_ids(session: AsyncSession, *, batch_size: int = 100) -> AsyncIterator[List[int]]:
    offset = 0
    while True:
        stmt = (
            select(organisations_table.c.id)
            .order_by(organisations_table.c.id.asc())
            .offset(offset)
            .limit(batch_size)
        )
        result = await session.execute(stmt)
        ids = [row.id for row in result.fetchall()]
        if not ids:
            break
        yield ids
        offset += len(ids)
        if len(ids) < batch_size:
            break


__all__ = ["iter_org_ids", "organisations_table", "metadata"]

# backend/api/src/repositories/transaction.py
from __future__ import annotations
from datetime import datetime
from typing import Sequence, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Transaction
from ..schemas import TransactionCreate


class TransactionRepo:
    # ----------------- create / bulk -----------------

    async def create(self, session: AsyncSession, tx_in: TransactionCreate) -> Transaction:
        """
        Create a single transaction (no commit; caller decides).
        """
        tx = Transaction(**tx_in.model_dump())
        session.add(tx)
        await session.flush()  # get tx.id
        return tx

    async def bulk_insert(self, session: AsyncSession, rows: list[dict]) -> int:
        """
        Bulk insert rows shaped like Transaction(**row). No commit; caller decides.
        Returns number of inserted rows.
        """
        if not rows:
            return 0
        for r in rows:
            session.add(Transaction(**r))
        await session.flush()
        return len(rows)

    # ----------------- reads -----------------

    async def list_by_org(
        self,
        session: AsyncSession,
        org_id: int,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
        order_asc: bool = False,
    ) -> Sequence[Transaction]:
        stmt = select(Transaction).where(Transaction.org_id == org_id)
        stmt = stmt.order_by(Transaction.txn_date.asc() if order_asc else Transaction.txn_date.desc())
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        res = await session.execute(stmt)
        return list(res.scalars())

    async def list_by_upload(
        self,
        session: AsyncSession,
        org_id: int,
        upload_id: int,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Sequence[Transaction]:
        stmt = (
            select(Transaction)
            .where(Transaction.org_id == org_id, Transaction.upload_id == upload_id)
            .order_by(Transaction.txn_date.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        res = await session.execute(stmt)
        return list(res.scalars())

    async def window(
        self,
        session: AsyncSession,
        org_id: int,
        start: datetime,
        end: datetime,
        *,
        include_upload_id: Optional[int] = None,
    ) -> Sequence[Transaction]:
        """
        Return transactions in [start, end) for an org, optionally restricted to an upload.
        """
        stmt = select(Transaction).where(
            Transaction.org_id == org_id,
            Transaction.txn_date >= start,
            Transaction.txn_date < end,
        )
        if include_upload_id is not None:
            stmt = stmt.where(Transaction.upload_id == include_upload_id)
        stmt = stmt.order_by(Transaction.txn_date.asc())
        res = await session.execute(stmt)
        return list(res.scalars())

    # ----------------- deletes / maintenance -----------------

    async def delete_by_upload(self, session: AsyncSession, org_id: int, upload_id: int) -> int:
        """
        Delete all transactions for an org + upload. No commit; caller decides.
        Returns number of rows matched (DB may return 0 if not supported).
        """
        stmt = delete(Transaction).where(Transaction.org_id == org_id, Transaction.upload_id == upload_id)
        res = await session.execute(stmt)
        # some dialects don't return rowcount reliably; use res.rowcount when available
        return getattr(res, "rowcount", 0)

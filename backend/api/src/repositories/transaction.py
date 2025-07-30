from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Transaction
from ..schemas import TransactionCreate


class TransactionRepo:
    async def create(self, session: AsyncSession, tx_in: TransactionCreate) -> Transaction:
        tx = Transaction(**tx_in.model_dump())
        session.add(tx)
        await session.commit()
        await session.refresh(tx)
        return tx

    async def list_by_org(self, session: AsyncSession, org_id: int) -> list[Transaction]:
        result = await session.execute(select(Transaction).where(Transaction.org_id == org_id))
        return result.scalars().all()

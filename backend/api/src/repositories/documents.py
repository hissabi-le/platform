from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from ..models import Document

class DocumentRepo:
    async def list_by_org(self, db: AsyncSession, org_id: UUID) -> list[Document]:
        q = select(Document).where(Document.org_id == org_id)
        result = await db.execute(q)
        return result.scalars().all()

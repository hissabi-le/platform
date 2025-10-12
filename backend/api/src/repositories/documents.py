# backend/api/src/repositories/documents.py
from __future__ import annotations
from typing import Optional, Sequence

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Document


class DocumentRepo:
    # ------------- create -------------
    async def create(
        self,
        db: AsyncSession,
        *,
        org_id: int,
        filename: str,
        content_type: str,
        storage_path: str,
        size_bytes: int,
        doc_type: str = "generic",
        metadata: dict | None = None,
        upload_id: int | None = None,
    ) -> Document:
        doc = Document(
            org_id=org_id,
            upload_id=upload_id,
            filename=filename,
            content_type=content_type,
            storage_path=storage_path,
            size_bytes=size_bytes,
            doc_type=doc_type,
            metadata_json=metadata,
        )
        db.add(doc)
        await db.flush()  # populate doc.id
        return doc

    # ------------- reads -------------
    async def list_by_org(
        self,
        db: AsyncSession,
        org_id: int,
        *,
        limit: int | None = None,
        offset: int = 0,
        newest_first: bool = True,
    ) -> Sequence[Document]:
        stmt = select(Document).where(Document.org_id == org_id)
        stmt = stmt.order_by(Document.created_at.desc() if newest_first else Document.created_at.asc())
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        res = await db.execute(stmt)
        return list(res.scalars())

    # alias to match your earlier naming
    async def list(self, db: AsyncSession, org_id: int, **kwargs) -> Sequence[Document]:
        return await self.list_by_org(db, org_id, **kwargs)

    async def get_by_id(self, db: AsyncSession, doc_id: int) -> Optional[Document]:
        return await db.get(Document, doc_id)

    async def get_owned(self, db: AsyncSession, org_id: int, doc_id: int) -> Optional[Document]:
        return await db.scalar(
            select(Document).where(and_(Document.id == doc_id, Document.org_id == org_id))
        )

    async def search_by_filename(
        self,
        db: AsyncSession,
        org_id: int,
        q: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Document]:
        # simple ILIKE search; adjust for your dialect if needed
        pattern = f"%{q}%"
        stmt = (
            select(Document)
            .where(and_(Document.org_id == org_id, Document.filename.ilike(pattern)))
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await db.execute(stmt)
        return list(res.scalars())

    # ------------- updates -------------
    async def attach_upload(self, db: AsyncSession, doc: Document, upload_id: int | None) -> Document:
        doc.upload_id = upload_id
        db.add(doc)
        await db.flush()
        return doc

    async def update_metadata(self, db: AsyncSession, doc: Document, metadata: dict | None) -> Document:
        doc.metadata_json = metadata
        db.add(doc)
        await db.flush()
        return doc

    # ------------- deletes -------------
    async def delete(self, db: AsyncSession, doc: Document) -> None:
        await db.delete(doc)
        # no commit here; caller decides

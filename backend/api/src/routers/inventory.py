from __future__ import annotations

import os
import tempfile
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..assistant import OpenAIClient
from ..database import get_db
from ..excel_cleaner import clean_table, load_table
from ..models import Document, InventoryItem, InventoryMovement
from ..repositories.documents import DocumentRepo
from ..repositories.inventory import InventoryRepo
from ..security import AuthContext, require_plan
from ..schemas import (
    InventoryItemIn,
    InventoryItemOut,
    InventoryMovementIn,
    InventoryMovementRow,
    InventorySummaryRow,
)
from ..storage import load_file

router = APIRouter(prefix="/inventory", tags=["inventory"])
repo = InventoryRepo()
document_repo = DocumentRepo()

UNIT_ALIASES = {
    "kilograms": "kg",
    "kilos": "kg",
    "kg": "kg",
    "dozen": "dozen",
    "dz": "dozen",
    "pcs": "piece",
    "pieces": "piece",
    "unit": "unit",
}


def _norm_unit(value: str | None) -> str:
    if not value:
        return "unit"
    normalized = value.strip().lower()
    return UNIT_ALIASES.get(normalized, normalized)


@router.post("/items", response_model=InventoryItemOut, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: InventoryItemIn,
    auth: AuthContext = Depends(require_plan("inventory")),
    session: AsyncSession = Depends(get_db),
) -> InventoryItemOut:
    item = await repo.upsert_item(
        session,
        org_id=auth.user.org_id,
        name=payload.name,
        unit=payload.unit,
        sku=payload.sku,
        category=payload.category,
    )
    await session.commit()
    await session.refresh(item)
    return InventoryItemOut.model_validate(item, from_attributes=True)


@router.post("/movements", response_model=InventoryMovementRow, status_code=status.HTTP_201_CREATED)
async def add_movement(
    payload: InventoryMovementIn,
    auth: AuthContext = Depends(require_plan("inventory")),
    session: AsyncSession = Depends(get_db),
) -> InventoryMovementRow:
    item = await session.get(InventoryItem, payload.item_id)
    if not item or item.org_id != auth.user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    movement = await repo.add_movement(
        session,
        org_id=auth.user.org_id,
        item_id=item.id,
        qty_delta=float(payload.qty_delta),
        unit_cost=float(payload.unit_cost) if payload.unit_cost is not None else None,
        memo=payload.memo,
        ref_document_id=None,
    )
    await session.commit()
    await session.refresh(movement)
    return InventoryMovementRow(
        ts=movement.ts,
        quantity=float(movement.qty_delta),
        type="in" if movement.qty_delta >= 0 else "out",
        ref=movement.memo,
    )


@router.get("/summary", response_model=list[InventorySummaryRow])
async def inventory_summary(
    auth: AuthContext = Depends(require_plan("inventory")),
    session: AsyncSession = Depends(get_db),
):
    rows = await repo.summary(session, org_id=auth.user.org_id)
    return [
        InventorySummaryRow(
            item_id=row.id,
            name=row.name,
            unit=row.unit,
            on_hand=float(row.on_hand or 0),
            avg_unit_cost=float(row.avg_unit_cost) if row.avg_unit_cost is not None else None,
        )
        for row in rows
    ]


@router.get("/items/{item_id}/movements", response_model=list[InventoryMovementRow])
async def list_movements(
    item_id: int,
    auth: AuthContext = Depends(require_plan("inventory")),
    session: AsyncSession = Depends(get_db),
):
    item = await session.get(InventoryItem, item_id)
    if not item or item.org_id != auth.user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    movements = await repo.list_movements(session, org_id=auth.user.org_id, item_id=item_id)
    return [
        InventoryMovementRow(
            ts=m.ts,
            quantity=float(m.qty_delta),
            type="in" if m.qty_delta >= 0 else "out",
            ref=m.memo,
        )
        for m in movements
    ]


@router.post("/extract/{document_id}", response_model=dict)
async def inventory_extract(
    document_id: int,
    auth: AuthContext = Depends(require_plan("inventory")),
    session: AsyncSession = Depends(get_db),
):
    doc = await document_repo.get_owned(session, auth.user.org_id, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        data = load_file(doc.storage_path)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load document") from exc

    suffix = ""
    if doc.filename:
        suffix = os.path.splitext(doc.filename)[1]
    if not suffix:
        suffix = os.path.splitext(doc.storage_path)[1]
    tmp_kwargs: dict[str, Any] = {"delete": False}
    if suffix:
        tmp_kwargs["suffix"] = suffix
    with tempfile.NamedTemporaryFile(**tmp_kwargs) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        df = load_table(tmp_path)
        df = clean_table(df)
    finally:
        os.unlink(tmp_path)

    rows = df.to_dict(orient="records")
    llm = OpenAIClient()
    mapped = llm.map_rows_to_inventory(rows)

    created = 0
    try:
        for row in mapped:
            item_name = row.get("Item") or row.get("item")
            if not item_name:
                continue
            qty = row.get("Qty")
            try:
                qty_val = float(qty) if qty is not None else None
            except (TypeError, ValueError):
                qty_val = None
            if qty_val is None:
                continue
            unit = _norm_unit(row.get("Unit"))
            amount = row.get("Amount")
            try:
                unit_cost = (float(amount) / qty_val) if amount and qty_val else None
            except Exception:
                unit_cost = None

            item = await repo.upsert_item(
                session,
                org_id=auth.user.org_id,
                name=str(item_name),
                unit=unit,
                sku=row.get("SKU") if row.get("SKU") else None,
            )
            await repo.add_movement(
                session,
                org_id=auth.user.org_id,
                item_id=item.id,
                qty_delta=qty_val,
                unit_cost=unit_cost,
                memo="auto-LLM",
                ref_document_id=doc.id,
            )
            created += 1
    except Exception:
        await session.rollback()
        raise
    else:
        await session.commit()
    return {"created_movements": created}

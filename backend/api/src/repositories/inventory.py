from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Optional

from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import InventoryItem, InventoryMovement


class InventoryRepo:
    async def upsert_item(
        self,
        session: AsyncSession,
        *,
        org_id: int,
        name: str,
        unit: str,
        sku: str | None = None,
        category: str | None = None,
    ) -> InventoryItem:
        stmt = select(InventoryItem).where(
            InventoryItem.org_id == org_id,
            InventoryItem.name == name,
            InventoryItem.unit == unit,
        )
        item = await session.scalar(stmt)
        if item:
            if sku:
                item.sku = sku
            if category:
                item.category = category
        else:
            item = InventoryItem(org_id=org_id, name=name, unit=unit, sku=sku, category=category)
            session.add(item)
            await session.flush()
        return item

    async def add_movement(
        self,
        session: AsyncSession,
        *,
        org_id: int,
        item_id: int,
        qty_delta: float,
        unit_cost: float | None,
        memo: str | None,
        ref_document_id: int | None,
    ) -> InventoryMovement:
        movement = InventoryMovement(
            org_id=org_id,
            item_id=item_id,
            qty_delta=qty_delta,
            unit_cost=unit_cost,
            memo=memo,
            ref_document_id=ref_document_id,
        )
        session.add(movement)
        await session.flush()
        return movement

    async def list_movements(
        self,
        session: AsyncSession,
        *,
        org_id: int,
        item_id: int,
    ) -> list[InventoryMovement]:
        stmt = (
            select(InventoryMovement)
            .where(InventoryMovement.org_id == org_id, InventoryMovement.item_id == item_id)
            .order_by(InventoryMovement.ts.desc())
        )
        rows = await session.execute(stmt)
        return list(rows.scalars())

    async def summary(
        self,
        session: AsyncSession,
        *,
        org_id: int,
    ) -> Iterable[tuple[int, str, str, float, float | None]]:
        stmt = (
            select(
                InventoryItem.id,
                InventoryItem.name,
                InventoryItem.unit,
                func.coalesce(func.sum(InventoryMovement.qty_delta), 0).label("on_hand"),
                func.avg(InventoryMovement.unit_cost).label("avg_unit_cost"),
            )
            .join(InventoryMovement, InventoryMovement.item_id == InventoryItem.id, isouter=True)
            .where(InventoryItem.org_id == org_id)
            .group_by(InventoryItem.id)
            .order_by(InventoryItem.name)
        )
        rows = await session.execute(stmt)
        return rows.all()

    async def weighted_average_cost(
        self,
        session: AsyncSession,
        *,
        org_id: int,
        item_id: int,
    ) -> Optional[Decimal]:
        qty_expr = InventoryMovement.qty_delta
        value_expr = case(
            (
                InventoryMovement.unit_cost.isnot(None),
                InventoryMovement.qty_delta * InventoryMovement.unit_cost,
            ),
            else_=0,
        )
        stmt = (
            select(
                func.coalesce(func.sum(qty_expr), 0),
                func.coalesce(func.sum(value_expr), 0),
            )
            .where(
                InventoryMovement.org_id == org_id,
                InventoryMovement.item_id == item_id,
            )
        )
        qty, total_value = (await session.execute(stmt)).one()
        if qty is None or qty == 0:
            return None
        try:
            return Decimal(total_value) / Decimal(qty)
        except Exception:
            return None

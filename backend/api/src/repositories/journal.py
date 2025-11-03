from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal
from typing import Iterable, Optional, Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import JournalDay, JournalEntry, InventoryMovement, InventoryItem
from ..repositories.inventory import InventoryRepo
from ..repositories.settings import SettingsRepo


MONEY_QUANT = Decimal("0.0001")


def _quantize_money(value: Optional[Decimal]) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(value).quantize(MONEY_QUANT)


def _quantize_unit_cost(value: Optional[Decimal]) -> Optional[Decimal]:
    if value is None:
        return None
    return Decimal(value).quantize(Decimal("0.0001"))


class JournalRepo:
    def __init__(self) -> None:
        self.inventory_repo = InventoryRepo()
        self.settings_repo = SettingsRepo()

    @staticmethod
    def hash_payload(org_id: int, journal_date: date, raw_text: str) -> str:
        payload = f"{org_id}|{journal_date.isoformat()}|{raw_text.strip()}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    async def get_by_date(
        self,
        session: AsyncSession,
        *,
        org_id: int,
        journal_date: date,
    ) -> Optional[JournalDay]:
        return await session.scalar(
            select(JournalDay).where(
                JournalDay.org_id == org_id,
                JournalDay.journal_date == journal_date,
            )
        )

    async def list_entries(
        self,
        session: AsyncSession,
        *,
        journal_day_id: int,
    ) -> list[JournalEntry]:
        rows = await session.execute(
            select(JournalEntry).where(JournalEntry.journal_day_id == journal_day_id).order_by(JournalEntry.id.asc())
        )
        return list(rows.scalars())

    async def delete_entries(self, session: AsyncSession, journal_day_id: int) -> None:
        await session.execute(delete(JournalEntry).where(JournalEntry.journal_day_id == journal_day_id))

    def _classify_entry_for_totals(self, entry: dict) -> tuple[str, Decimal]:
        entry_type = entry["entry_type"]
        total = _quantize_money(entry.get("total"))
        if entry_type == "inventory_use":
            return "inventory_use", total
        if entry_type == "inventory_purchase":
            # inventory purchases impact balance sheet rather than immediate p&l
            return "inventory_purchase", Decimal("0")
        if entry_type == "revenue":
            return "revenue", total
        if entry_type == "transfer":
            return "transfer", Decimal("0")
        return "cost", total

    def _compute_totals(
        self,
        entries: Sequence[dict],
    ) -> tuple[Decimal, Decimal]:
        revenue_total = Decimal("0")
        cost_total = Decimal("0")
        for entry in entries:
            bucket, amount = self._classify_entry_for_totals(entry)
            if bucket == "revenue":
                revenue_total += amount
            elif bucket == "cost":
                cost_total += amount
            elif bucket == "inventory_use":
                cost_total += amount
        return revenue_total.quantize(MONEY_QUANT), cost_total.quantize(MONEY_QUANT)

    async def preview_totals(
        self,
        session: AsyncSession,
        *,
        org_id: int,
        entries: Sequence[dict],
    ) -> tuple[Decimal, Decimal, Decimal, Decimal, Optional[float]]:
        working = [dict(entry) for entry in entries]
        await self._apply_inventory_movements(
            session,
            org_id=org_id,
            entries=working,
            day_id=None,
            persist=False,
        )
        for original, updated in zip(entries, working):
            original.update(updated)
        revenue_total, cost_total = self._compute_totals(working)
        net = (revenue_total - cost_total).quantize(MONEY_QUANT)
        cumulative = await self.settings_repo.cumulative_net_profit(session, org_id)
        cumulative = (cumulative + net).quantize(MONEY_QUANT)

        settings = await self.settings_repo.ensure(session, org_id)
        roi = None
        if settings.total_initial_investment and settings.total_initial_investment > 0:
            roi = float((cumulative / settings.total_initial_investment * Decimal("100")).quantize(Decimal("0.01")))
        return revenue_total, cost_total, net, cumulative, roi

    async def replace_entries(
        self,
        session: AsyncSession,
        *,
        day: JournalDay,
        org_id: int,
        entries: Sequence[dict],
    ) -> list[JournalEntry]:
        await self.delete_entries(session, day.id)
        stored: list[JournalEntry] = []
        for payload in entries:
            entry = JournalEntry(
                org_id=org_id,
                journal_day_id=day.id,
                entry_type=payload["entry_type"],
                item_name=payload.get("item_name"),
                quantity=payload.get("quantity"),
                unit=payload.get("unit"),
                unit_cost=payload.get("unit_cost"),
                total=payload.get("total"),
                category=payload.get("category"),
                vat_percent=payload.get("vat_percent"),
                vat_included=payload.get("vat_included"),
                notes=payload.get("notes"),
                ambiguous=payload.get("ambiguous", False),
                clarification_question=payload.get("clarification_question"),
                resolved=payload.get("resolved", True),
            )
            session.add(entry)
            stored.append(entry)
        await session.flush()
        return stored

    async def _clear_journal_movements(
        self,
        session: AsyncSession,
        *,
        org_id: int,
        day_id: int,
    ) -> None:
        memo_tag = f"journal:day:{day_id}"
        await session.execute(
            delete(InventoryMovement).where(
                InventoryMovement.org_id == org_id,
                InventoryMovement.memo == memo_tag,
            )
        )

    async def _apply_inventory_movements(
        self,
        session: AsyncSession,
        *,
        org_id: int,
        entries: Sequence[dict],
        day_id: Optional[int],
        persist: bool,
    ) -> None:
        item_cache: dict[tuple[str, str], int] = {}
        memo_tag = f"journal:day:{day_id}" if day_id is not None else None
        for entry in entries:
            if entry.get("ambiguous") or not entry.get("resolved"):
                continue
            entry_type = entry["entry_type"]
            if entry_type not in {"inventory_purchase", "inventory_use"}:
                continue
            item_name = (entry.get("item_name") or "").strip()
            if not item_name:
                continue
            unit = (entry.get("unit") or "unit").strip()
            qty = entry.get("quantity")
            if qty is None:
                continue
            qty = Decimal(qty)
            key = (item_name.lower(), unit.lower())
            if key not in item_cache:
                if persist:
                    item = await self.inventory_repo.upsert_item(
                        session,
                        org_id=org_id,
                        name=item_name,
                        unit=unit,
                        sku=None,
                        category=None,
                    )
                    item_cache[key] = item.id
                else:
                    existing = (
                        await session.execute(
                            select(InventoryItem.id).where(
                                InventoryItem.org_id == org_id,
                                InventoryItem.name == item_name,
                                InventoryItem.unit == unit,
                            )
                        )
                    ).scalar_one_or_none()
                    if existing is None:
                        entry["ambiguous"] = True
                        entry["resolved"] = False
                        entry["clarification_question"] = (
                            entry.get("clarification_question")
                            or "inventory item not found; please create it before recording usage"
                        )
                        continue
                    item_cache[key] = existing
            item_id = item_cache[key]
            if entry_type == "inventory_purchase":
                unit_cost = entry.get("unit_cost")
                total = entry.get("total")
                if unit_cost is None and total is not None and qty != 0:
                    unit_cost = Decimal(total) / qty
                unit_cost = _quantize_unit_cost(unit_cost)
                entry["unit_cost"] = unit_cost
                if persist:
                    await self.inventory_repo.add_movement(
                        session,
                        org_id=org_id,
                        item_id=item_id,
                        qty_delta=float(qty),
                        unit_cost=float(unit_cost) if unit_cost is not None else None,
                        memo=memo_tag or "journal purchase",
                        ref_document_id=None,
                    )
            elif entry_type == "inventory_use":
                unit_cost = entry.get("unit_cost")
                if unit_cost is None:
                    wac = await self.inventory_repo.weighted_average_cost(session, org_id=org_id, item_id=item_id)
                    unit_cost = wac
                unit_cost = _quantize_unit_cost(unit_cost)
                if unit_cost is None:
                    entry["ambiguous"] = True
                    entry["resolved"] = False
                    entry["clarification_question"] = (
                        entry.get("clarification_question")
                        or "unable to determine inventory cost, please review stock levels"
                    )
                    continue
                entry["unit_cost"] = unit_cost
                entry["total"] = _quantize_money(unit_cost * qty)
                if persist:
                    await self.inventory_repo.add_movement(
                        session,
                        org_id=org_id,
                        item_id=item_id,
                        qty_delta=float(-qty),
                        unit_cost=float(unit_cost),
                        memo=memo_tag or "journal usage",
                        ref_document_id=None,
                    )

    async def persist_day(
        self,
        session: AsyncSession,
        *,
        org_id: int,
        user_id: Optional[int],
        journal_date: date,
        raw_text: str,
        language: str,
        hash_key: str,
        entries: Sequence[dict],
    ) -> tuple[JournalDay, list[JournalEntry], Decimal, Decimal, Decimal, Decimal, Optional[float]]:
        settings = await self.settings_repo.ensure(session, org_id)
        day = await self.get_by_date(session, org_id=org_id, journal_date=journal_date)
        if not day:
            day = JournalDay(
                org_id=org_id,
                user_id=user_id,
                journal_date=journal_date,
                raw_text=raw_text,
                language=language,
                hash_key=hash_key,
            )
            session.add(day)
            await session.flush()
        day.user_id = user_id
        day.raw_text = raw_text
        day.language = language
        day.hash_key = hash_key

        await self._clear_journal_movements(session, org_id=org_id, day_id=day.id)
        await self._apply_inventory_movements(
            session,
            org_id=org_id,
            entries=entries,
            day_id=day.id,
            persist=True,
        )
        stored_entries = await self.replace_entries(session, day=day, org_id=org_id, entries=entries)

        revenue_total, cost_total = self._compute_totals(entries)
        net = (revenue_total - cost_total).quantize(MONEY_QUANT)
        unresolved = sum(1 for entry in entries if entry.get("ambiguous") or not entry.get("resolved", True))

        day.total_revenue = revenue_total
        day.total_cost = cost_total
        day.net_profit = net
        day.parse_status = "needs_review" if unresolved else "parsed"
        day.clarification_count = unresolved

        cumulative = await self.settings_repo.cumulative_net_profit(session, org_id)
        cumulative = cumulative.quantize(MONEY_QUANT)
        roi = None
        if settings.total_initial_investment and settings.total_initial_investment > 0:
            roi = float((cumulative / settings.total_initial_investment * Decimal("100")).quantize(Decimal("0.01")))

        return day, stored_entries, revenue_total, cost_total, net, cumulative, roi

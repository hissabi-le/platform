from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Iterable, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..assistant import OpenAIClient
from ..cache.analytics_cache import analytics_cache
from ..database import get_db
from ..models import JournalDay
from ..repositories.journal import JournalRepo
from ..repositories.settings import SettingsRepo
from ..schemas import (
    JournalClarification,
    JournalDayMeta,
    JournalDayRequest,
    JournalDayResponse,
    JournalEntryRead,
    JournalResolveRequest,
    JournalTotals,
)
from ..security import AuthContext, require_plan


router = APIRouter(prefix="/journal", tags=["journal"])
assistant_client = OpenAIClient()
journal_repo = JournalRepo()
settings_repo = SettingsRepo()


def _parse_date(value: Optional[str]) -> date:
    if not value:
        return datetime.now(timezone.utc).date()
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid date format; expected yyyy-mm-dd") from exc


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    normalised = dict(entry)
    for field in ("quantity", "unit_cost", "total", "vat_percent"):
        value = normalised.get(field)
        if value is None:
            continue
        try:
            normalised[field] = Decimal(str(value))
        except Exception:
            normalised[field] = None
            normalised["ambiguous"] = True
            normalised["resolved"] = False
            normalised.setdefault("clarification_question", f"unable to parse numeric value for {field}")
    if "ambiguous" not in normalised:
        normalised["ambiguous"] = False
    if "resolved" not in normalised:
        normalised["resolved"] = not normalised["ambiguous"]
    return normalised


def _build_clarifications(entries: Iterable[dict[str, Any]], with_ids: bool) -> list[JournalClarification]:
    clarifications: list[JournalClarification] = []
    for entry in entries:
        if entry.get("ambiguous") or not entry.get("resolved", True):
            clarifications.append(
                JournalClarification(
                    entry_id=entry.get("id") if with_ids else None,
                    question=entry.get("clarification_question") or "please review this entry",
                    entry_type=entry.get("entry_type", "cost"),
                    category=entry.get("category"),
                )
            )
    return clarifications


def _entries_to_schema(entries: Iterable[dict[str, Any]]) -> list[JournalEntryRead]:
    payload: list[JournalEntryRead] = []
    for entry in entries:
        payload.append(
            JournalEntryRead(
                id=entry.get("id"),
                entry_type=entry.get("entry_type"),
                item_name=entry.get("item_name"),
                quantity=entry.get("quantity"),
                unit=entry.get("unit"),
                unit_cost=entry.get("unit_cost"),
                total=entry.get("total"),
                category=entry.get("category"),
                vat_percent=entry.get("vat_percent"),
                vat_included=entry.get("vat_included"),
                notes=entry.get("notes"),
                ambiguous=entry.get("ambiguous", False),
                clarification_question=entry.get("clarification_question"),
                resolved=entry.get("resolved", True),
                created_at=entry.get("created_at"),
            )
        )
    return payload


@router.post("/day", response_model=JournalDayResponse)
async def save_journal_day(
    payload: JournalDayRequest,
    auth: AuthContext = Depends(require_plan("analytics_basic")),
    session: AsyncSession = Depends(get_db),
) -> JournalDayResponse:
    journal_date = _parse_date(payload.date)
    lines = payload.raw_text.splitlines()
    parsed = assistant_client.parse_journal_lines(lines, locale=None)
    entries = [_normalize_entry(entry) for entry in parsed.get("entries", [])]
    language = parsed.get("language") or "en"
    commit = payload.commit if payload.commit is not None else True

    if not entries:
        raise HTTPException(
            status_code=400,
            detail="Could not parse any journal entries. Please enter text like 'sold 5 coffees for $25' or 'paid rent $400'."
        )

    if not commit:
        revenue, cost, net, cumulative, roi = await journal_repo.preview_totals(
            session,
            org_id=auth.user.org_id,
            entries=entries,
        )
        clarifications = _build_clarifications(entries, with_ids=False)
        now = datetime.now(timezone.utc)
        totals = JournalTotals(
            revenue=revenue,
            cost=cost,
            net=net,
            cumulative_net=cumulative,
            roi=roi,
        )
        meta = JournalDayMeta(
            id=None,
            org_id=auth.user.org_id,
            user_id=auth.user.id,
            journal_date=journal_date,
            language=language,
            parse_status="needs_review" if clarifications else "parsed",
            total_revenue=revenue,
            total_cost=cost,
            net_profit=net,
            clarification_count=len(clarifications),
            created_at=now,
            updated_at=now,
        )
        return JournalDayResponse(
            journal_day=meta,
            entries=_entries_to_schema(entries),
            clarifications=clarifications,
            totals=totals,
        )

    hash_key = journal_repo.hash_payload(auth.user.org_id, journal_date, payload.raw_text)
    day, stored_entries, revenue, cost, net, cumulative, roi = await journal_repo.persist_day(
        session,
        org_id=auth.user.org_id,
        user_id=auth.user.id,
        journal_date=journal_date,
        raw_text=payload.raw_text,
        language=language,
        hash_key=hash_key,
        entries=entries,
    )
    await session.flush()
    await session.refresh(day)
    for entry in stored_entries:
        await session.refresh(entry)
    await session.commit()
    
    # Invalidate analytics cache so fresh data is fetched
    await analytics_cache.clear_org(auth.user.org_id)

    stored_dicts = [
        {
            "id": entry.id,
            "entry_type": entry.entry_type,
            "item_name": entry.item_name,
            "quantity": entry.quantity,
            "unit": entry.unit,
            "unit_cost": entry.unit_cost,
            "total": entry.total,
            "category": entry.category,
            "vat_percent": entry.vat_percent,
            "vat_included": entry.vat_included,
            "notes": entry.notes,
            "ambiguous": entry.ambiguous,
            "clarification_question": entry.clarification_question,
            "resolved": entry.resolved,
            "created_at": entry.created_at,
        }
        for entry in stored_entries
    ]

    clarifications = _build_clarifications(stored_dicts, with_ids=True)
    totals = JournalTotals(
        revenue=revenue,
        cost=cost,
        net=net,
        cumulative_net=cumulative,
        roi=roi,
    )
    meta = JournalDayMeta(
        id=day.id,
        org_id=day.org_id,
        user_id=day.user_id,
        journal_date=day.journal_date,
        language=day.language,
        parse_status=day.parse_status,
        total_revenue=day.total_revenue,
        total_cost=day.total_cost,
        net_profit=day.net_profit,
        clarification_count=day.clarification_count,
        created_at=day.created_at,
        updated_at=day.updated_at,
    )

    return JournalDayResponse(
        journal_day=meta,
        entries=_entries_to_schema(stored_dicts),
        clarifications=clarifications,
        totals=totals,
    )


@router.get("/day", response_model=JournalDayResponse)
async def get_journal_day(
    date_str: Optional[str] = None,
    auth: AuthContext = Depends(require_plan("analytics_basic")),
    session: AsyncSession = Depends(get_db),
) -> JournalDayResponse:
    journal_date = _parse_date(date_str)
    day = await journal_repo.get_by_date(session, org_id=auth.user.org_id, journal_date=journal_date)
    if not day:
        raise HTTPException(status_code=404, detail="journal day not found")
    entries = await journal_repo.list_entries(session, journal_day_id=day.id)
    stored_dicts = [
        {
            "id": entry.id,
            "entry_type": entry.entry_type,
            "item_name": entry.item_name,
            "quantity": entry.quantity,
            "unit": entry.unit,
            "unit_cost": entry.unit_cost,
            "total": entry.total,
            "category": entry.category,
            "vat_percent": entry.vat_percent,
            "vat_included": entry.vat_included,
            "notes": entry.notes,
            "ambiguous": entry.ambiguous,
            "clarification_question": entry.clarification_question,
            "resolved": entry.resolved,
            "created_at": entry.created_at,
        }
        for entry in entries
    ]
    clarifications = _build_clarifications(stored_dicts, with_ids=True)
    settings = await settings_repo.ensure(session, auth.user.org_id)
    cumulative = await settings_repo.cumulative_net_profit(session, auth.user.org_id)
    roi = None
    if settings.total_initial_investment and settings.total_initial_investment > 0:
        roi = float((cumulative / settings.total_initial_investment * Decimal("100")).quantize(Decimal("0.01")))
    totals = JournalTotals(
        revenue=day.total_revenue,
        cost=day.total_cost,
        net=day.net_profit,
        cumulative_net=cumulative.quantize(Decimal("0.0001")),
        roi=roi,
    )
    meta = JournalDayMeta(
        id=day.id,
        org_id=day.org_id,
        user_id=day.user_id,
        journal_date=day.journal_date,
        language=day.language,
        parse_status=day.parse_status,
        total_revenue=day.total_revenue,
        total_cost=day.total_cost,
        net_profit=day.net_profit,
        clarification_count=day.clarification_count,
        created_at=day.created_at,
        updated_at=day.updated_at,
    )
    return JournalDayResponse(
        journal_day=meta,
        entries=_entries_to_schema(stored_dicts),
        clarifications=clarifications,
        totals=totals,
    )


@router.patch("/day/{journal_day_id}/resolve", response_model=JournalDayResponse)
async def resolve_journal_day(
    journal_day_id: int,
    payload: JournalResolveRequest,
    auth: AuthContext = Depends(require_plan("analytics_basic")),
    session: AsyncSession = Depends(get_db),
) -> JournalDayResponse:
    day = await session.get(JournalDay, journal_day_id)
    if not day or day.org_id != auth.user.org_id:
        raise HTTPException(status_code=404, detail="journal day not found")
    entries = await journal_repo.list_entries(session, journal_day_id=day.id)
    entry_map = {entry.id: entry for entry in entries}

    for resolution in payload.resolutions:
        entry = entry_map.get(resolution.entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"journal entry {resolution.entry_id} not found")
        if resolution.entry_type is not None:
            entry.entry_type = resolution.entry_type
        if resolution.treat_as_inventory is not None:
            entry.entry_type = "inventory_purchase" if resolution.treat_as_inventory else "cost"
        if resolution.category is not None:
            entry.category = resolution.category
        if resolution.quantity is not None:
            entry.quantity = resolution.quantity
        if resolution.vat_percent is not None:
            entry.vat_percent = resolution.vat_percent
        if resolution.vat_included is not None:
            entry.vat_included = resolution.vat_included
        if resolution.unit is not None:
            entry.unit = resolution.unit
        if resolution.unit_cost is not None:
            entry.unit_cost = resolution.unit_cost
        if resolution.notes is not None:
            entry.notes = resolution.notes
        entry.ambiguous = False
        entry.resolved = True
        entry.clarification_question = None

    entry_payload = [
        {
            "entry_type": entry.entry_type,
            "item_name": entry.item_name,
            "quantity": entry.quantity,
            "unit": entry.unit,
            "unit_cost": entry.unit_cost,
            "total": entry.total,
            "category": entry.category,
            "vat_percent": entry.vat_percent,
            "vat_included": entry.vat_included,
            "notes": entry.notes,
            "ambiguous": entry.ambiguous,
            "clarification_question": entry.clarification_question,
            "resolved": entry.resolved,
        }
        for entry in entries
    ]

    hash_key = day.hash_key
    day, stored_entries, revenue, cost, net, cumulative, roi = await journal_repo.persist_day(
        session,
        org_id=auth.user.org_id,
        user_id=day.user_id,
        journal_date=day.journal_date,
        raw_text=day.raw_text,
        language=day.language or "en",
        hash_key=hash_key,
        entries=entry_payload,
        append=False,  # Resolve replaces, not appends
    )
    await session.flush()
    await session.refresh(day)
    for entry in stored_entries:
        await session.refresh(entry)
    await session.commit()

    stored_dicts = [
        {
            "id": entry.id,
            "entry_type": entry.entry_type,
            "item_name": entry.item_name,
            "quantity": entry.quantity,
            "unit": entry.unit,
            "unit_cost": entry.unit_cost,
            "total": entry.total,
            "category": entry.category,
            "vat_percent": entry.vat_percent,
            "vat_included": entry.vat_included,
            "notes": entry.notes,
            "ambiguous": entry.ambiguous,
            "clarification_question": entry.clarification_question,
            "resolved": entry.resolved,
            "created_at": entry.created_at,
        }
        for entry in stored_entries
    ]
    clarifications = _build_clarifications(stored_dicts, with_ids=True)
    totals = JournalTotals(
        revenue=revenue,
        cost=cost,
        net=net,
        cumulative_net=cumulative,
        roi=roi,
    )
    meta = JournalDayMeta(
        id=day.id,
        org_id=day.org_id,
        user_id=day.user_id,
        journal_date=day.journal_date,
        language=day.language,
        parse_status=day.parse_status,
        total_revenue=day.total_revenue,
        total_cost=day.total_cost,
        net_profit=day.net_profit,
        clarification_count=day.clarification_count,
        created_at=day.created_at,
        updated_at=day.updated_at,
    )

    return JournalDayResponse(
        journal_day=meta,
        entries=_entries_to_schema(stored_dicts),
        clarifications=clarifications,
        totals=totals,
    )


@router.patch("/entry/{entry_id}/payment-status")
async def toggle_payment_status(
    entry_id: int,
    status: str,  # "paid" | "unpaid"
    auth: AuthContext = Depends(require_plan("analytics_basic")),
    session: AsyncSession = Depends(get_db),
):
    """Toggle payment status for a journal entry. Used for AR/AP tracking."""
    from sqlalchemy import select, update
    from ..models import JournalEntry
    
    if status not in ("paid", "unpaid"):
        raise HTTPException(status_code=400, detail="status must be 'paid' or 'unpaid'")
    
    # Verify entry exists and belongs to user's org
    query = select(JournalEntry).where(
        JournalEntry.id == entry_id,
        JournalEntry.org_id == auth.user.org_id,
    )
    result = await session.execute(query)
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    
    # Update payment status
    payment_date = datetime.now(timezone.utc) if status == "paid" else None
    entry.payment_status = status
    entry.payment_date = payment_date
    
    await session.commit()
    
    return {
        "id": entry.id,
        "payment_status": status,
        "payment_date": payment_date.isoformat() if payment_date else None,
    }

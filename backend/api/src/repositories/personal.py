# src/repositories/personal.py
"""Repository for Hisabi Personal - personal expense/income tracking."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import PersonalEntry, PersonalBudget, PersonalCategory


class PersonalRepo:
    """Repository for personal finance entries and budgets."""

    # ==================== Entries ====================

    async def create_entry(
        self,
        session: AsyncSession,
        user_id: int,
        entry_date: date,
        entry_type: str,
        category: str,
        amount: Decimal,
        currency: str = "USD",
        description: Optional[str] = None,
        vendor: Optional[str] = None,
        notes: Optional[str] = None,
        ai_categorized: bool = False,
    ) -> PersonalEntry:
        """Create a new personal finance entry."""
        entry = PersonalEntry(
            user_id=user_id,
            entry_date=entry_date,
            entry_type=entry_type,
            category=category,
            amount=amount,
            currency=currency,
            description=description,
            vendor=vendor,
            notes=notes,
            ai_categorized=ai_categorized,
        )
        session.add(entry)
        await session.flush()
        return entry

    async def list_entries(
        self,
        session: AsyncSession,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None,
        entry_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PersonalEntry]:
        """List entries with optional filters."""
        stmt = select(PersonalEntry).where(PersonalEntry.user_id == user_id)

        if start_date:
            stmt = stmt.where(PersonalEntry.entry_date >= start_date)
        if end_date:
            stmt = stmt.where(PersonalEntry.entry_date <= end_date)
        if category:
            stmt = stmt.where(PersonalEntry.category == category)
        if entry_type:
            stmt = stmt.where(PersonalEntry.entry_type == entry_type)

        stmt = stmt.order_by(desc(PersonalEntry.entry_date), desc(PersonalEntry.id))
        stmt = stmt.limit(limit).offset(offset)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_entry_by_id(
        self,
        session: AsyncSession,
        user_id: int,
        entry_id: int,
    ) -> Optional[PersonalEntry]:
        """Get a single entry by ID."""
        stmt = select(PersonalEntry).where(
            and_(PersonalEntry.id == entry_id, PersonalEntry.user_id == user_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_entry(
        self,
        session: AsyncSession,
        entry: PersonalEntry,
        **updates: Any,
    ) -> PersonalEntry:
        """Update an entry with given fields."""
        for key, value in updates.items():
            if hasattr(entry, key) and value is not None:
                setattr(entry, key, value)
        await session.flush()
        return entry

    async def delete_entry(
        self,
        session: AsyncSession,
        entry: PersonalEntry,
    ) -> None:
        """Delete an entry."""
        await session.delete(entry)
        await session.flush()

    # ==================== Analytics ====================

    async def get_summary(
        self,
        session: AsyncSession,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Decimal]:
        """Get total income, expenses, and net for a date range."""
        stmt = select(
            PersonalEntry.entry_type,
            func.sum(PersonalEntry.amount).label("total"),
        ).where(
            and_(
                PersonalEntry.user_id == user_id,
                PersonalEntry.entry_date >= start_date,
                PersonalEntry.entry_date <= end_date,
            )
        ).group_by(PersonalEntry.entry_type)

        result = await session.execute(stmt)
        rows = result.all()

        totals = {"income": Decimal("0"), "expense": Decimal("0")}
        for row in rows:
            totals[row.entry_type] = row.total or Decimal("0")

        totals["net"] = totals["income"] - totals["expense"]
        return totals

    async def get_category_breakdown(
        self,
        session: AsyncSession,
        user_id: int,
        start_date: date,
        end_date: date,
        entry_type: str = "expense",
    ) -> List[Dict[str, Any]]:
        """Get spending breakdown by category (for pie chart)."""
        stmt = select(
            PersonalEntry.category,
            func.sum(PersonalEntry.amount).label("total"),
            func.count(PersonalEntry.id).label("count"),
        ).where(
            and_(
                PersonalEntry.user_id == user_id,
                PersonalEntry.entry_type == entry_type,
                PersonalEntry.entry_date >= start_date,
                PersonalEntry.entry_date <= end_date,
            )
        ).group_by(PersonalEntry.category).order_by(desc("total"))

        result = await session.execute(stmt)
        return [
            {"category": row.category, "total": float(row.total), "count": row.count}
            for row in result.all()
        ]

    async def get_monthly_trends(
        self,
        session: AsyncSession,
        user_id: int,
        months: int = 12,
    ) -> List[Dict[str, Any]]:
        """Get monthly income/expense trends (for bar chart)."""
        end_date = date.today()
        start_date = date(end_date.year, end_date.month, 1) - timedelta(days=months * 30)

        stmt = select(
            func.date_trunc("month", PersonalEntry.entry_date).label("month"),
            PersonalEntry.entry_type,
            func.sum(PersonalEntry.amount).label("total"),
        ).where(
            and_(
                PersonalEntry.user_id == user_id,
                PersonalEntry.entry_date >= start_date,
            )
        ).group_by("month", PersonalEntry.entry_type).order_by("month")

        result = await session.execute(stmt)
        rows = result.all()

        # Pivot by month
        months_data: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            month_str = row.month.strftime("%Y-%m")
            if month_str not in months_data:
                months_data[month_str] = {"month": month_str, "income": 0, "expense": 0}
            months_data[month_str][row.entry_type] = float(row.total)

        return list(months_data.values())

    async def get_top_spending(
        self,
        session: AsyncSession,
        user_id: int,
        days: int = 30,
        category: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get top spending items/vendors in a time period."""
        start_date = date.today() - timedelta(days=days)

        stmt = select(
            PersonalEntry.description,
            PersonalEntry.vendor,
            PersonalEntry.category,
            func.sum(PersonalEntry.amount).label("total"),
            func.count(PersonalEntry.id).label("count"),
        ).where(
            and_(
                PersonalEntry.user_id == user_id,
                PersonalEntry.entry_type == "expense",
                PersonalEntry.entry_date >= start_date,
            )
        )

        if category:
            stmt = stmt.where(PersonalEntry.category == category)

        # Group by vendor or description
        stmt = stmt.group_by(
            PersonalEntry.description,
            PersonalEntry.vendor,
            PersonalEntry.category,
        ).order_by(desc("total")).limit(limit)

        result = await session.execute(stmt)
        return [
            {
                "description": row.description or row.vendor or "Unknown",
                "vendor": row.vendor,
                "category": row.category,
                "total": float(row.total),
                "count": row.count,
            }
            for row in result.all()
        ]

    async def get_insights(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> Dict[str, Any]:
        """Get personalized insights for greeting message."""
        today = date.today()
        week_ago = today - timedelta(days=7)
        two_weeks_ago = today - timedelta(days=14)
        month_start = date(today.year, today.month, 1)

        # This week's spending
        this_week = await self.get_summary(session, user_id, week_ago, today)
        # Last week's spending
        last_week = await self.get_summary(session, user_id, two_weeks_ago, week_ago)
        # This month's totals
        this_month = await self.get_summary(session, user_id, month_start, today)

        # Top category this month
        top_categories = await self.get_category_breakdown(
            session, user_id, month_start, today, "expense"
        )

        week_change = 0
        if last_week["expense"] > 0:
            week_change = ((this_week["expense"] - last_week["expense"]) / last_week["expense"]) * 100

        return {
            "this_week_expense": float(this_week["expense"]),
            "this_week_income": float(this_week["income"]),
            "week_change_percent": round(float(week_change), 1),
            "this_month_expense": float(this_month["expense"]),
            "this_month_income": float(this_month["income"]),
            "this_month_net": float(this_month["net"]),
            "top_category": top_categories[0]["category"] if top_categories else None,
            "top_category_amount": top_categories[0]["total"] if top_categories else 0,
        }

    # ==================== Budgets ====================

    async def list_budgets(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> List[PersonalBudget]:
        """List all budgets for a user."""
        stmt = select(PersonalBudget).where(PersonalBudget.user_id == user_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_budget_by_category(
        self,
        session: AsyncSession,
        user_id: int,
        category: str,
    ) -> Optional[PersonalBudget]:
        """Get budget for a specific category."""
        stmt = select(PersonalBudget).where(
            and_(PersonalBudget.user_id == user_id, PersonalBudget.category == category)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_budget(
        self,
        session: AsyncSession,
        user_id: int,
        category: str,
        monthly_limit: Decimal,
    ) -> PersonalBudget:
        """Create or update a budget for a category."""
        existing = await self.get_budget_by_category(session, user_id, category)
        if existing:
            existing.monthly_limit = monthly_limit
            await session.flush()
            return existing

        budget = PersonalBudget(
            user_id=user_id,
            category=category,
            monthly_limit=monthly_limit,
        )
        session.add(budget)
        await session.flush()
        return budget

    async def delete_budget(
        self,
        session: AsyncSession,
        budget: PersonalBudget,
    ) -> None:
        """Delete a budget."""
        await session.delete(budget)
        await session.flush()

    async def get_budget_progress(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> List[Dict[str, Any]]:
        """Get all budgets with current month spending progress."""
        today = date.today()
        month_start = date(today.year, today.month, 1)

        budgets = await self.list_budgets(session, user_id)
        category_totals = await self.get_category_breakdown(
            session, user_id, month_start, today, "expense"
        )

        # Map category -> spent
        spent_map = {item["category"]: item["total"] for item in category_totals}

        return [
            {
                "category": b.category,
                "monthly_limit": float(b.monthly_limit),
                "spent": spent_map.get(b.category, 0),
                "remaining": float(b.monthly_limit) - spent_map.get(b.category, 0),
                "percent_used": round(
                    (spent_map.get(b.category, 0) / float(b.monthly_limit)) * 100, 1
                ) if b.monthly_limit > 0 else 0,
            }
            for b in budgets
        ]

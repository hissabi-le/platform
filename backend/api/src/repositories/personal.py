# src/repositories/personal.py
"""Repository for Hisabi Personal - personal expense/income tracking."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import PersonalEntry, PersonalBudget, PersonalCategory, PersonalAccount


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
        # Intervals:
        # This week: (today-7, today]
        # Last week: (today-14, today-7]
        week_ago = today - timedelta(days=7)
        two_weeks_ago = today - timedelta(days=14)
        month_start = date(today.year, today.month, 1)
        
        query_start = min(two_weeks_ago, month_start)

        # Optimization: Fetch all relevant entries in one query
        # Fix: Limit increased to ensure coverage; date sort allows optimization if needed
        entries = await self.list_entries(
            session, user_id, start_date=query_start, limit=5000
        )

        this_week = {"income": 0.0, "expense": 0.0}
        last_week = {"income": 0.0, "expense": 0.0}
        this_month = {"income": 0.0, "expense": 0.0}
        categories: Dict[str, float] = {}

        for e in entries:
            amt = float(e.amount)
            # This Week: week_ago < date <= today
            if e.entry_date > week_ago and e.entry_date <= today:
                 this_week[e.entry_type] += amt
            
            # Last Week: two_weeks_ago < date <= week_ago
            if e.entry_date > two_weeks_ago and e.entry_date <= week_ago:
                 last_week[e.entry_type] += amt

            # This Month: month_start <= date <= today
            if e.entry_date >= month_start and e.entry_date <= today:
                 this_month[e.entry_type] += amt
                 if e.entry_type == "expense":
                     categories[e.category] = categories.get(e.category, 0.0) + amt
        
        this_month_net = this_month["income"] - this_month["expense"]
        
        week_change = 0.0
        if last_week["expense"] > 0:
            week_change = ((this_week["expense"] - last_week["expense"]) / last_week["expense"]) * 100
            
        # Top category
        top_cat_name = None
        top_cat_amount = 0.0
        if categories:
            # Sort by amount desc
            best_cat = max(categories.items(), key=lambda x: x[1])
            top_cat_name = best_cat[0]
            top_cat_amount = best_cat[1]

        return {
            "this_week_expense": this_week["expense"],
            "this_week_income": this_week["income"],
            "week_change_percent": round(week_change, 1),
            "this_month_expense": this_month["expense"],
            "this_month_income": this_month["income"],
            "this_month_net": this_month_net,
            "top_category": top_cat_name,
            "top_category_amount": top_cat_amount,
        }

    # ==================== Accounts ====================

    async def list_accounts(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> List[PersonalAccount]:
        """List all accounts for a user."""
        stmt = select(PersonalAccount).where(PersonalAccount.user_id == user_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create_account(
        self,
        session: AsyncSession,
        user_id: int,
        name: str,
        balance: Decimal,
        type: str,
    ) -> PersonalAccount:
        """Create a new account."""
        account = PersonalAccount(
            user_id=user_id,
            name=name,
            balance=balance,
            type=type,
        )
        session.add(account)
        await session.flush()
        return account

    async def get_account(
        self,
        session: AsyncSession,
        user_id: int,
        account_id: int,
    ) -> Optional[PersonalAccount]:
         stmt = select(PersonalAccount).where(
            and_(PersonalAccount.id == account_id, PersonalAccount.user_id == user_id)
         )
         result = await session.execute(stmt)
         return result.scalar_one_or_none()

    async def delete_account(
        self,
        session: AsyncSession,
        account: PersonalAccount,
    ) -> None:
        """Delete an account."""
        await session.delete(account)
        await session.flush()


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

    # ==================== The Flow (Sankey) ====================

    async def get_flow_data(
        self,
        session: AsyncSession,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """Generate Sankey diagram data: Income → Category → Merchant."""
        # Get income totals
        income_stmt = select(
            func.sum(PersonalEntry.amount).label("total"),
        ).where(
            and_(
                PersonalEntry.user_id == user_id,
                PersonalEntry.entry_type == "income",
                PersonalEntry.entry_date >= start_date,
                PersonalEntry.entry_date <= end_date,
            )
        )
        income_result = await session.execute(income_stmt)
        total_income = float(income_result.scalar() or 0)

        # Get expense by category
        category_stmt = select(
            PersonalEntry.category,
            func.sum(PersonalEntry.amount).label("total"),
        ).where(
            and_(
                PersonalEntry.user_id == user_id,
                PersonalEntry.entry_type == "expense",
                PersonalEntry.entry_date >= start_date,
                PersonalEntry.entry_date <= end_date,
            )
        ).group_by(PersonalEntry.category).order_by(desc("total"))

        category_result = await session.execute(category_stmt)
        categories = category_result.all()

        # Get expense by category + vendor
        vendor_stmt = select(
            PersonalEntry.category,
            PersonalEntry.vendor,
            func.sum(PersonalEntry.amount).label("total"),
        ).where(
            and_(
                PersonalEntry.user_id == user_id,
                PersonalEntry.entry_type == "expense",
                PersonalEntry.entry_date >= start_date,
                PersonalEntry.entry_date <= end_date,
                PersonalEntry.vendor.isnot(None),
            )
        ).group_by(PersonalEntry.category, PersonalEntry.vendor).order_by(desc("total")).limit(20)

        vendor_result = await session.execute(vendor_stmt)
        vendors = vendor_result.all()

        # Build nodes and links for Sankey
        nodes = [{"id": "income", "label": "Income", "value": total_income}]
        links = []

        # Add category nodes and income→category links
        for cat in categories:
            cat_id = f"cat_{cat.category}"
            nodes.append({"id": cat_id, "label": cat.category, "value": float(cat.total)})
            links.append({
                "source": "income",
                "target": cat_id,
                "value": float(cat.total),
            })

        # Add vendor nodes and category→vendor links
        seen_vendors = set()
        for v in vendors:
            if v.vendor:
                vendor_id = f"vendor_{v.vendor[:20]}"
                if vendor_id not in seen_vendors:
                    nodes.append({"id": vendor_id, "label": v.vendor[:20], "value": float(v.total)})
                    seen_vendors.add(vendor_id)
                links.append({
                    "source": f"cat_{v.category}",
                    "target": vendor_id,
                    "value": float(v.total),
                })

        return {
            "nodes": nodes,
            "links": links,
            "total_income": total_income,
            "total_expense": sum(float(c.total) for c in categories),
        }

    # ==================== Merchant DNA ====================

    async def get_top_merchants(
        self,
        session: AsyncSession,
        user_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top merchants by total spend."""
        stmt = select(
            PersonalEntry.vendor,
            func.sum(PersonalEntry.amount).label("total"),
            func.count(PersonalEntry.id).label("count"),
            func.min(PersonalEntry.entry_date).label("first_visit"),
            func.max(PersonalEntry.entry_date).label("last_visit"),
        ).where(
            and_(
                PersonalEntry.user_id == user_id,
                PersonalEntry.entry_type == "expense",
                PersonalEntry.vendor.isnot(None),
            )
        ).group_by(PersonalEntry.vendor).order_by(desc("total")).limit(limit)

        result = await session.execute(stmt)
        return [
            {
                "vendor": row.vendor,
                "total_spend": float(row.total),
                "visit_count": row.count,
                "first_visit": row.first_visit.isoformat() if row.first_visit else None,
                "last_visit": row.last_visit.isoformat() if row.last_visit else None,
                "avg_order": round(float(row.total) / row.count, 2) if row.count > 0 else 0,
            }
            for row in result.all()
        ]

    async def get_merchant_profile(
        self,
        session: AsyncSession,
        user_id: int,
        vendor: str,
    ) -> Optional[Dict[str, Any]]:
        """Get detailed profile for a specific merchant."""
        # Basic stats
        stats_stmt = select(
            func.sum(PersonalEntry.amount).label("total"),
            func.count(PersonalEntry.id).label("count"),
            func.avg(PersonalEntry.amount).label("avg"),
            func.min(PersonalEntry.entry_date).label("first_visit"),
            func.max(PersonalEntry.entry_date).label("last_visit"),
        ).where(
            and_(
                PersonalEntry.user_id == user_id,
                PersonalEntry.vendor == vendor,
            )
        )

        stats_result = await session.execute(stats_stmt)
        stats = stats_result.one_or_none()

        if not stats or not stats.total:
            return None

        # Day of week frequency
        dow_stmt = select(
            func.extract("dow", PersonalEntry.entry_date).label("dow"),
            func.count(PersonalEntry.id).label("count"),
        ).where(
            and_(
                PersonalEntry.user_id == user_id,
                PersonalEntry.vendor == vendor,
            )
        ).group_by("dow")

        dow_result = await session.execute(dow_stmt)
        dow_data = {int(row.dow): row.count for row in dow_result.all()}
        days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        frequency_by_day = [{"day": days[i], "count": dow_data.get(i, 0)} for i in range(7)]

        # Monthly trend (last 6 months)
        six_months_ago = date.today() - timedelta(days=180)
        trend_stmt = select(
            func.date_trunc("month", PersonalEntry.entry_date).label("month"),
            func.sum(PersonalEntry.amount).label("total"),
            func.avg(PersonalEntry.amount).label("avg"),
        ).where(
            and_(
                PersonalEntry.user_id == user_id,
                PersonalEntry.vendor == vendor,
                PersonalEntry.entry_date >= six_months_ago,
            )
        ).group_by("month").order_by("month")

        trend_result = await session.execute(trend_stmt)
        price_trend = [
            {
                "month": row.month.strftime("%Y-%m"),
                "total": float(row.total),
                "avg": round(float(row.avg), 2),
            }
            for row in trend_result.all()
        ]

        # Calculate visit frequency
        if stats.first_visit and stats.last_visit:
            days_span = (stats.last_visit - stats.first_visit).days or 1
            visits_per_week = (stats.count / days_span) * 7
        else:
            visits_per_week = 0

        return {
            "vendor": vendor,
            "lifetime_spend": float(stats.total),
            "visit_count": stats.count,
            "average_order": round(float(stats.avg), 2),
            "first_visit": stats.first_visit.isoformat() if stats.first_visit else None,
            "last_visit": stats.last_visit.isoformat() if stats.last_visit else None,
            "visits_per_week": round(visits_per_week, 1),
            "frequency_by_day": frequency_by_day,
            "price_trend": price_trend,
        }

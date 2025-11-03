from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import OrganisationSettings, JournalDay


class SettingsRepo:
    async def get(self, session: AsyncSession, org_id: int) -> Optional[OrganisationSettings]:
        return await session.scalar(
            select(OrganisationSettings).where(OrganisationSettings.org_id == org_id)
        )

    async def ensure(self, session: AsyncSession, org_id: int) -> OrganisationSettings:
        settings = await self.get(session, org_id)
        if settings:
            return settings
        settings = OrganisationSettings(org_id=org_id)
        session.add(settings)
        await session.flush()
        return settings

    async def update(
        self,
        session: AsyncSession,
        org_id: int,
        *,
        total_initial_investment: Optional[Decimal] = None,
        starting_cash_balance: Optional[Decimal] = None,
        current_assets_value: Optional[Decimal] = None,
        default_currency: Optional[str] = None,
        default_locale: Optional[str] = None,
        vat_rate: Optional[Decimal] = None,
    ) -> OrganisationSettings:
        settings = await self.ensure(session, org_id)
        if total_initial_investment is not None:
            settings.total_initial_investment = total_initial_investment
        if starting_cash_balance is not None:
            settings.starting_cash_balance = starting_cash_balance
        if current_assets_value is not None:
            settings.current_assets_value = current_assets_value
        if default_currency is not None:
            settings.default_currency = default_currency
        if default_locale is not None:
            settings.default_locale = default_locale
        if vat_rate is not None:
            settings.vat_rate = vat_rate
        session.add(settings)
        await session.flush()
        return settings

    async def cumulative_net_profit(self, session: AsyncSession, org_id: int) -> Decimal:
        stmt = select(func.coalesce(func.sum(JournalDay.net_profit), 0)).where(JournalDay.org_id == org_id)
        value = (await session.execute(stmt)).scalar_one()
        return Decimal(value or 0)

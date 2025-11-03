from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..repositories.settings import SettingsRepo
from ..schemas import OrganisationSettingsRead, OrganisationSettingsUpdate
from ..security import AuthContext, require_plan

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/org", response_model=OrganisationSettingsRead)
async def get_org_settings(
    auth: AuthContext = Depends(require_plan("analytics_basic")),
    session: AsyncSession = Depends(get_db),
) -> OrganisationSettingsRead:
    repo = SettingsRepo()
    settings = await repo.ensure(session, auth.user.org_id)
    await session.commit()
    await session.refresh(settings)
    return OrganisationSettingsRead.model_validate(settings, from_attributes=True)


@router.put("/org", response_model=OrganisationSettingsRead)
async def update_org_settings(
    payload: OrganisationSettingsUpdate,
    auth: AuthContext = Depends(require_plan("analytics_basic")),
    session: AsyncSession = Depends(get_db),
) -> OrganisationSettingsRead:
    repo = SettingsRepo()
    settings = await repo.update(
        session,
        auth.user.org_id,
        total_initial_investment=payload.total_initial_investment,
        starting_cash_balance=payload.starting_cash_balance,
        current_assets_value=payload.current_assets_value,
        default_currency=payload.default_currency,
        default_locale=payload.default_locale,
        vat_rate=payload.vat_rate,
    )
    await session.commit()
    await session.refresh(settings)
    return OrganisationSettingsRead.model_validate(settings, from_attributes=True)

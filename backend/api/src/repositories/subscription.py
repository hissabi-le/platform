from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Subscription


class SubscriptionRepo:
    async def get_by_org(self, session: AsyncSession, org_id: int) -> Subscription | None:
        result = await session.execute(select(Subscription).where(Subscription.org_id == org_id))
        return result.scalar_one_or_none()

    async def upsert_from_stripe_event(self, session: AsyncSession, event: dict) -> Subscription:
        # placeholder implementation
        stripe_id = event.get("data", {}).get("object", {}).get("id")
        sub = await self.get_by_org(session, event.get("org_id", 0))  # type: ignore
        if sub:
            sub.status = event.get("data", {}).get("object", {}).get("status", "")
        else:
            sub = Subscription(org_id=event.get("org_id", 0), stripe_subscription_id=stripe_id, plan="", status="")
            session.add(sub)
        await session.commit()
        await session.refresh(sub)
        return sub

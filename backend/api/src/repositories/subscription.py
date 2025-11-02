# backend/api/src/repositories/subscription.py
from __future__ import annotations
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..cache.subscription_cache import subscription_cache
from ..models import Subscription


class SubscriptionRepo:
    # ---------- reads ----------
    async def get_by_org(self, session: AsyncSession, org_id: int) -> Optional[Subscription]:
        return await session.scalar(
            select(Subscription).where(Subscription.org_id == org_id)
        )

    async def active_for_org(self, session: AsyncSession, org_id: int) -> Optional[Subscription]:
        return await session.scalar(
            select(Subscription).where(
                Subscription.org_id == org_id,
                Subscription.status == "active",
            )
        )

    # ---------- writes (no commit; caller decides) ----------
    async def set_status(self, session: AsyncSession, org_id: int, status: str) -> Optional[Subscription]:
        sub = await self.get_by_org(session, org_id)
        if not sub:
            return None
        sub.status = status
        session.add(sub)
        await session.flush()
        await subscription_cache.invalidate(org_id)
        return sub

    async def set_plan(self, session: AsyncSession, org_id: int, plan: str) -> Optional[Subscription]:
        sub = await self.get_by_org(session, org_id)
        if not sub:
            return None
        sub.plan = plan
        session.add(sub)
        await session.flush()
        await subscription_cache.invalidate(org_id)
        return sub

    async def upsert_from_stripe_event(
        self,
        session: AsyncSession,
        event: dict,
        *,
        fallback_org_id: int | None = None,
    ) -> Optional[Subscription]:
        """
        Create or update a subscription record from a Stripe webhook event.
        Prefers org_id in event['data']['object']['metadata']['org_id'].
        Returns the upserted Subscription or None if org_id cannot be determined.
        """
        etype = (event or {}).get("type", "")
        obj = (event or {}).get("data", {}).get("object", {}) or {}

        # Determine org_id (prefer metadata)
        meta = obj.get("metadata") or {}
        org_id_val = meta.get("org_id") or fallback_org_id
        if org_id_val is None:
            # If you map customer->org elsewhere, hook it here.
            return None
        try:
            org_id = int(org_id_val)
        except Exception:
            return None

        stripe_sub_id = obj.get("id")
        status = obj.get("status") or "active"

        # Derive plan nickname/id if available
        plan = None
        try:
            items = (obj.get("items") or {}).get("data") or []
            if items:
                price = (items[0] or {}).get("price") or {}
                plan = price.get("nickname") or price.get("id")
        except Exception:
            plan = None
        plan = plan or "starter"

        # Upsert
        sub = await self.get_by_org(session, org_id)
        if sub:
            if stripe_sub_id:
                sub.stripe_subscription_id = stripe_sub_id
            sub.status = status
            sub.plan = plan
        else:
            sub = Subscription(
                org_id=org_id,
                stripe_subscription_id=stripe_sub_id or "",
                status=status,
                plan=plan,
            )
            session.add(sub)

        # Optional: normalize canceled events
        if etype.endswith(".deleted") or status == "canceled":
            sub.status = "canceled"

        await session.flush()
        await subscription_cache.invalidate(org_id)
        return sub

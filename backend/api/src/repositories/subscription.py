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

    async def get_by_stripe_id(
        self, session: AsyncSession, stripe_subscription_id: str
    ) -> Optional[Subscription]:
        return await session.scalar(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_subscription_id
            )
        )

    async def upsert_from_stripe_event(
        self,
        session: AsyncSession,
        event: dict,
        *,
        fallback_org_id: int | None = None,
    ) -> Optional[Subscription]:
        """
        Create or update a subscription record from a Stripe webhook event.

        Handles the full lifecycle:
          - customer.subscription.created / .updated / .deleted
          - invoice.payment_succeeded / .payment_failed
          - checkout.session.completed (when subscription metadata.org_id is set)

        For subscription.* events, the org is identified via
        event.data.object.metadata.org_id (set when creating the Checkout
        session). For invoice.* events, we look up the existing row by
        stripe_subscription_id.
        """
        etype = (event or {}).get("type", "")
        obj = (event or {}).get("data", {}).get("object", {}) or {}

        if etype.startswith("invoice."):
            return await self._handle_invoice_event(session, etype, obj)

        # Subscription events (.created, .updated, .deleted) + checkout.session.completed
        meta = obj.get("metadata") or {}
        org_id_val = meta.get("org_id") or fallback_org_id
        if org_id_val is None:
            return None
        try:
            org_id = int(org_id_val)
        except Exception:
            return None

        # For checkout.session.completed, the subscription id is in `subscription`
        stripe_sub_id = obj.get("id")
        if etype == "checkout.session.completed":
            stripe_sub_id = obj.get("subscription") or stripe_sub_id

        status = obj.get("status") or "active"

        # Derive plan nickname/id if available
        plan: Optional[str] = None
        try:
            items = (obj.get("items") or {}).get("data") or []
            if items:
                price = (items[0] or {}).get("price") or {}
                plan = price.get("nickname") or price.get("id")
        except Exception:
            plan = None
        plan = plan or "starter"

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

        if etype.endswith(".deleted") or status == "canceled":
            sub.status = "canceled"

        await session.flush()
        await subscription_cache.invalidate(org_id)
        return sub

    async def _handle_invoice_event(
        self, session: AsyncSession, etype: str, obj: dict
    ) -> Optional[Subscription]:
        """Map invoice.payment_succeeded/failed to subscription status."""
        stripe_sub_id = obj.get("subscription")
        if not stripe_sub_id:
            return None
        sub = await self.get_by_stripe_id(session, stripe_sub_id)
        if not sub:
            return None

        if etype == "invoice.payment_failed":
            sub.status = "past_due"
        elif etype == "invoice.payment_succeeded":
            sub.status = "active"

        await session.flush()
        await subscription_cache.invalidate(sub.org_id)
        return sub

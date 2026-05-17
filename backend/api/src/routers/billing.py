"""Stripe Checkout + Customer Portal endpoints.

Frontend flow:
  1. User clicks Upgrade -> POST /billing/checkout-session?plan=pro
  2. We return { url } pointing at Stripe-hosted Checkout
  3. After payment, Stripe redirects to FRONTEND_URL/settings/billing/success
  4. The customer.subscription.created webhook updates the DB row

Manage subscription / cancel: POST /billing/portal-session -> Stripe Customer
Portal URL.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..repositories.subscription import SubscriptionRepo
from ..security import AuthContext, current_user

router = APIRouter(prefix="/billing", tags=["billing"])

logger = logging.getLogger(__name__)


PlanTier = Literal["starter", "pro"]


def _price_id_for(plan: PlanTier) -> str | None:
    if plan == "starter":
        return settings.stripe_price_id_starter
    if plan == "pro":
        return settings.stripe_price_id_pro
    return None


@router.post("/checkout-session")
async def create_checkout_session(
    plan: PlanTier = "pro",
    auth: AuthContext = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing is not configured.")
    price_id = _price_id_for(plan)
    if not price_id:
        raise HTTPException(
            status_code=400,
            detail=f"No Stripe price configured for plan '{plan}'.",
        )

    import stripe  # local import keeps the dep optional at module load

    stripe.api_key = settings.stripe_secret_key

    success_url = f"{settings.frontend_url.rstrip('/')}/settings/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{settings.frontend_url.rstrip('/')}/settings/billing/cancel"

    try:
        # Stripe SDK is synchronous; isolate it from the event loop.
        session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=auth.user.email,
            client_reference_id=str(auth.user.org_id),
            metadata={"org_id": str(auth.user.org_id), "plan": plan},
            subscription_data={
                "metadata": {"org_id": str(auth.user.org_id), "plan": plan},
            },
            allow_promotion_codes=True,
        )
    except Exception as exc:
        logger.exception("stripe checkout session create failed")
        # Don't leak Stripe internals to clients.
        raise HTTPException(status_code=502, detail="Billing provider error") from exc

    if not session.url:
        raise HTTPException(status_code=502, detail="Stripe did not return a URL")
    return {"url": session.url}


@router.post("/portal-session")
async def create_portal_session(
    auth: AuthContext = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing is not configured.")

    sub = await SubscriptionRepo().get_by_org(db, auth.user.org_id)
    if not sub or not sub.stripe_subscription_id:
        raise HTTPException(
            status_code=400,
            detail="No active subscription found for this account.",
        )

    import stripe

    stripe.api_key = settings.stripe_secret_key

    try:
        retrieved = await asyncio.to_thread(
            stripe.Subscription.retrieve, sub.stripe_subscription_id
        )
        customer_id = retrieved.get("customer") if isinstance(retrieved, dict) else retrieved.customer
        if not customer_id:
            raise ValueError("subscription is missing a customer id")
        portal = await asyncio.to_thread(
            stripe.billing_portal.Session.create,
            customer=customer_id,
            return_url=f"{settings.frontend_url.rstrip('/')}/settings/billing",
        )
    except Exception as exc:
        logger.exception("stripe portal session create failed")
        raise HTTPException(status_code=502, detail="Billing provider error") from exc

    return {"url": portal.url}

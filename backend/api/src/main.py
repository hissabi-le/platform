"""basic api service"""

import os

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import CookieTransport, AuthenticationBackend, JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from .database import get_db, async_session, engine
from .models import Base, User
from .repositories.subscription import SubscriptionRepo
from .schemas import UserCreate, UserRead

app = FastAPI()
VERSION = "0.1.0"
app.add_event_handler("startup", on_startup)


async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


cookie_transport = CookieTransport(cookie_max_age=3600)


def get_jwt_strategy() -> JWTStrategy:
    secret = os.getenv("SECRET", "changeme")
    return JWTStrategy(secret=secret, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)


async def get_user_db() -> SQLAlchemyUserDatabase:
    async with async_session() as session:
        yield SQLAlchemyUserDatabase(session, User)


fastapi_users = FastAPIUsers[User, int](
    get_user_db,
    [auth_backend],
)

current_user = fastapi_users.current_user(active=True)


@app.get("/healthz")
async def healthz(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/version")
async def version():
    return {"version": VERSION}


app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)


def get_current_active_user(allowed_roles: list[str] | None = None):
    async def dependency(user: User = Depends(current_user)) -> User:
        if not user.is_active:
            raise HTTPException(status_code=400, detail="inactive user")
        if allowed_roles and user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="forbidden")
        return user

    return dependency


async def require_plan(plan_name: str):
    async def dep(
        user: User = Depends(get_current_active_user()),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        repo = SubscriptionRepo()
        sub = await repo.get_by_org(db, user.org_id)
        if not sub or sub.plan != plan_name or sub.status != "active":
            raise HTTPException(status_code=402, detail="payment required")
        return user

    return dep


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    import stripe

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="invalid signature") from exc

    if event["type"] in {"invoice.paid", "customer.subscription.updated"}:
        repo = SubscriptionRepo()
        await repo.upsert_from_stripe_event(db, event)
    return {"status": "ok"}

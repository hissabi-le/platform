from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..cache.login_lockout_cache import login_lockout_cache
from ..database import get_db
from ..models import Subscription, User
from ..rate_limit import enforce_login_rate_limit
from ..repositories.user import UserRepo
from ..schemas import (
    AuthResponse,
    TokenPair,
    TokenRefreshRequest,
    UserCreate,
    UserLogin,
    UserOut,
)
from ..security import (
    AuthContext,
    create_access_token,
    create_refresh_token,
    current_user,
    decode_refresh_token,
    revoke_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])



async def _get_plan(session: AsyncSession, org_id: int) -> str | None:
    # 1. Try active/trialing first
    stmt = select(Subscription).where(
        Subscription.org_id == org_id,
        Subscription.status.in_(("active", "trialing"))
    )
    sub = await session.scalar(stmt)
    if sub:
        return sub.plan
    
    # 2. Fallback to any subscription
    stmt = select(Subscription).where(Subscription.org_id == org_id)
    sub = await session.scalar(stmt)
    if sub:
        return sub.plan
    # Personal mode is available without an active subscription.
    return "personal"


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    session: AsyncSession = Depends(get_db),
) -> AuthResponse:
    repo = UserRepo()
    existing = await repo.by_email(session, payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = await repo.create_with_org(session, payload.email, payload.password, payload.org_name, role="admin")

    # specific plan for personal demo? No, standard register is starter.
    subscription = Subscription(
        org_id=user.org_id,
        stripe_subscription_id=f"starter-{user.org_id}",
        plan="starter",
        status="active",
    )
    session.add(subscription)
    await session.commit()
    await session.refresh(user)

    user_out = UserOut.model_validate(user, from_attributes=True)
    user_out.plan = "starter"

    return AuthResponse(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user),
        user=user_out,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: UserLogin,
    _: None = Depends(enforce_login_rate_limit),
    session: AsyncSession = Depends(get_db),
) -> AuthResponse:
    # Per-account lockout — defends a single email against distributed
    # password-spraying that the per-IP rate limiter can't see.
    if await login_lockout_cache.is_locked(payload.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Account temporarily locked due to repeated failed sign-ins. "
                f"Try again in ~{login_lockout_cache.lockout_seconds // 60} minutes."
            ),
        )

    repo = UserRepo()
    user = await repo.by_email(session, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        # Don't reveal whether the email exists — log the failure regardless.
        await login_lockout_cache.record_failure(payload.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User disabled")

    # Clear the counter on success.
    await login_lockout_cache.clear(payload.email)

    plan = await _get_plan(session, user.org_id)
    user_out = UserOut.model_validate(user, from_attributes=True)
    user_out.plan = plan

    return AuthResponse(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user),
        user=user_out,
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: TokenRefreshRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenPair:
    decoded = await decode_refresh_token(payload.refresh_token)
    user = await session.get(User, decoded.sub)
    if user is None or not user.is_active or user.org_id != decoded.org:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Rotation: invalidate the presented refresh token so it can't be replayed.
    await revoke_token(decoded)

    return TokenPair(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: TokenRefreshRequest | None = None,
    auth: AuthContext = Depends(current_user),
) -> None:
    """Revoke the current access token and, if provided, the refresh token.

    Subsequent requests with these tokens will receive 401. Clients should
    additionally discard their local copies.
    """
    await revoke_token(auth.payload)
    if payload and payload.refresh_token:
        try:
            decoded = await decode_refresh_token(payload.refresh_token)
        except HTTPException:
            return  # already-invalid refresh token is a no-op
        if decoded.sub == auth.user.id:
            await revoke_token(decoded)


@router.get("/me", response_model=UserOut)
async def me(
    auth: AuthContext = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> UserOut:
    plan = await _get_plan(session, auth.user.org_id)
    user_out = UserOut.model_validate(auth.user, from_attributes=True)
    user_out.plan = plan
    return user_out

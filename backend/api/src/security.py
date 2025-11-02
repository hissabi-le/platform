from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
import base64
import hashlib
import hmac
import json
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .cache.subscription_cache import subscription_cache
from .config import settings
from .database import get_db
from .models import Subscription, User


try:  # Prefer PyJWT if available
    import jwt as _jwt_backend  # type: ignore

    if not hasattr(_jwt_backend, "encode") or not hasattr(_jwt_backend, "decode"):
        raise ImportError("PyJWT encode/decode not available")

    JWTError = getattr(_jwt_backend, "PyJWTError", Exception)

    def _jwt_encode(payload: dict[str, Any], secret: str) -> str:
        token = _jwt_backend.encode(payload, secret, algorithm="HS256")
        return token if isinstance(token, str) else token.decode("ascii")

    def _jwt_decode(token: str, secret: str) -> dict[str, Any]:
        return _jwt_backend.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )

except Exception:  # Fallback minimal HS256 implementation

    class JWTError(Exception):
        """Generic JWT error fallback."""

    class _JWTSignatureError(JWTError):
        pass

    class _JWTExpiredError(JWTError):
        pass

    def _b64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    def _b64url_decode(data: str) -> bytes:
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding)

    def _jwt_encode(payload: dict[str, Any], secret: str) -> str:
        header = {"typ": "JWT", "alg": "HS256"}
        header_json = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
        payload_json = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
        segments = [_b64url_encode(header_json), _b64url_encode(payload_json)]
        signing_input = ".".join(segments).encode("ascii")
        signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        segments.append(_b64url_encode(signature))
        return ".".join(segments)

    def _jwt_decode(token: str, secret: str) -> dict[str, Any]:
        try:
            header_b64, payload_b64, signature_b64 = token.split(".")
        except ValueError as exc:  # pragma: no cover - defensive
            raise JWTError("Invalid token structure") from exc

        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        signature = _b64url_decode(signature_b64)
        expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise _JWTSignatureError("Signature verification failed")

        header = json.loads(_b64url_decode(header_b64))
        if header.get("alg") != "HS256":
            raise JWTError("Unsupported JWT algorithm")

        payload = json.loads(_b64url_decode(payload_b64))
        exp = payload.get("exp")
        if exp is not None:
            now = int(datetime.now(timezone.utc).timestamp())
            if now >= int(exp):
                raise _JWTExpiredError("Token expired")
        return payload


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    sub: int
    org: int
    role: str
    type: TokenType
    exp: int
    iat: int
    iss: str | None = None
    jti: str | None = None


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
http_bearer = HTTPBearer(auto_error=False)

FEATURE_MATRIX: dict[str, set[str]] = {
    "starter": {"documents", "inventory", "analytics_basic"},
    "pro": {"documents", "inventory", "analytics_basic", "analytics_advanced", "assistant"},
    "enterprise": {"documents", "inventory", "analytics_basic", "analytics_advanced", "assistant", "api"},
}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(password, hashed)
    except Exception:
        return False


def _create_token(
    user: User,
    token_type: TokenType,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "org": user.org_id,
        "role": user.role,
        "type": token_type.value,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "iss": settings.jwt_issuer,
        "jti": uuid.uuid4().hex,
    }
    return _jwt_encode(payload, settings.jwt_secret)


def create_access_token(user: User) -> str:
    return _create_token(user, TokenType.ACCESS, timedelta(minutes=settings.jwt_access_minutes))


def create_refresh_token(user: User) -> str:
    return _create_token(user, TokenType.REFRESH, timedelta(days=settings.jwt_refresh_days))


def decode_token(token: str, expected_type: TokenType) -> TokenPayload:
    try:
        payload = _jwt_decode(token, settings.jwt_secret)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    try:
        data = TokenPayload.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload") from exc

    if data.type != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    if data.iss and data.iss != settings.jwt_issuer:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid issuer")
    return data


async def _extract_credentials(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(http_bearer),
) -> TokenPayload:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")
    payload = decode_token(creds.credentials, expected_type=TokenType.ACCESS)
    request.state.auth_payload = payload
    return payload


@dataclass(slots=True)
class AuthContext:
    user: User
    payload: TokenPayload
    subscription_plan: str | None = None


async def current_user(
    payload: TokenPayload = Depends(_extract_credentials),
    session: AsyncSession = Depends(get_db),
) -> AuthContext:
    user = await session.get(User, payload.sub)
    if not user or not user.is_active or user.org_id != payload.org:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return AuthContext(user=user, payload=payload)


async def current_user_with_active_subscription(
    auth: AuthContext = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> AuthContext:
    cached = await subscription_cache.get(auth.user.org_id)
    if cached:
        cached_status = cached.get("status")
        plan = cached.get("plan")
        if cached_status in {"active", "trialing"} and plan:
            auth.subscription_plan = plan
            return auth
        elif cached_status:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Subscription required")

    sub_stmt = select(Subscription).where(
        Subscription.org_id == auth.user.org_id,
        Subscription.status.in_(("active", "trialing")),
    )
    sub = await session.scalar(sub_stmt)
    if not sub:
        await subscription_cache.set(auth.user.org_id, {"status": "inactive"})
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Subscription required")
    auth.subscription_plan = sub.plan
    await subscription_cache.set(auth.user.org_id, {"status": sub.status, "plan": sub.plan})
    return auth


def decode_refresh_token(token: str) -> TokenPayload:
    return decode_token(token, expected_type=TokenType.REFRESH)


def require_plan(feature: str):
    async def _inner(auth: AuthContext = Depends(current_user_with_active_subscription)) -> AuthContext:
        plan = auth.subscription_plan or "starter"
        allowed = FEATURE_MATRIX.get(plan, set())
        if feature not in allowed:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Upgrade required")
        return auth

    return _inner

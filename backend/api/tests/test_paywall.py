import asyncio
import os

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

try:
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    from src.security import require_plan
    from src.cache.subscription_cache import subscription_cache
    from src.database import Base, async_session, engine
    from src.models import Organisation, Subscription, User
    from src.security import create_access_token, hash_password
except Exception as exc:  # pragma: no cover - handled via skip
    pytest.skip(f"Required dependencies not installed: {exc}", allow_module_level=True)


async def _init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


asyncio.run(_init_db())
asyncio.run(subscription_cache.clear())

app = FastAPI()


@app.get("/protected")
async def protected(_: User = Depends(require_plan("assistant"))):
    return {"ok": True}


@app.get("/personal-protected")
async def personal_protected(_: User = Depends(require_plan("personal"))):
    return {"ok": True}


client = TestClient(app)


async def _create_user_with_plan(plan: str | None, status: str = "active") -> User:
    async with async_session() as session:
        org = Organisation(name=f"org-{plan or 'none'}")
        session.add(org)
        await session.flush()
        user = User(
            org_id=org.id,
            email=f"user-{plan or 'none'}@test.com",
            hashed_password=hash_password("secret123"),
            role="user",
        )
        session.add(user)
        if plan:
            session.add(
                Subscription(
                    org_id=org.id,
                    stripe_subscription_id=f"sub-{plan}",
                    plan=plan,
                    status=status,
                )
            )
        await session.commit()
        await subscription_cache.invalidate(org.id)
        await session.refresh(user)
        return user


def _auth_header_for(user: User) -> dict[str, str]:
    token = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


def test_require_plan_denies_without_subscription():
    user = asyncio.run(_create_user_with_plan(plan=None))
    response = client.get("/protected", headers=_auth_header_for(user))
    assert response.status_code == 402


def test_require_plan_denies_without_feature():
    user = asyncio.run(_create_user_with_plan(plan="starter"))
    response = client.get("/protected", headers=_auth_header_for(user))
    assert response.status_code == 402


def test_require_plan_allows_when_feature_available():
    user = asyncio.run(_create_user_with_plan(plan="pro"))
    response = client.get("/protected", headers=_auth_header_for(user))
    assert response.status_code == 200


def test_require_plan_allows_personal_without_subscription():
    user = asyncio.run(_create_user_with_plan(plan=None))
    response = client.get("/personal-protected", headers=_auth_header_for(user))
    assert response.status_code == 200

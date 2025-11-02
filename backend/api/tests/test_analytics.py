import asyncio
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.cache.analytics_cache import analytics_cache
from src.cache.subscription_cache import subscription_cache
from src.database import Base, async_session, engine
from src.main import app
from src.models import Organisation, Subscription, Transaction, User
from src.security import create_access_token, hash_password

pytest.importorskip("sqlalchemy")


async def _init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


asyncio.run(_init_db())

client = TestClient(app)


async def _prepare_user() -> User:
    async with async_session() as session:
        org = Organisation(name="analytics-org")
        session.add(org)
        await session.flush()
        user = User(
            org_id=org.id,
            email="analytics@test.com",
            hashed_password=hash_password("secret123"),
            role="admin",
        )
        session.add(user)
        session.add(
            Subscription(
                org_id=org.id,
                stripe_subscription_id=f"sub-{org.id}",
                plan="pro",
                status="active",
            )
        )
        await session.flush()
        now = datetime.utcnow()
        session.add_all(
            [
                Transaction(
                    org_id=org.id,
                    upload_id=None,
                    txn_date=now - timedelta(days=10),
                    account_code="Sales",
                    category="Revenue",
                    amount=1000,
                    currency="USD",
                    description="Sale",
                ),
                Transaction(
                    org_id=org.id,
                    upload_id=None,
                    txn_date=now - timedelta(days=5),
                    account_code="Rent",
                    category="Expense",
                    amount=-300,
                    currency="USD",
                    description="Rent",
                ),
            ]
        )
        await session.commit()
        await subscription_cache.invalidate(org.id)
        return user


@pytest.mark.asyncio
async def test_analytics_pnl_endpoint():
    user = await _prepare_user()
    await analytics_cache.clear()
    headers = {"Authorization": f"Bearer {create_access_token(user)}"}
    response = client.get("/analytics/pnl?range=1m", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["revenue"] == 1000
    assert data["expenses"] == 300
    assert isinstance(data["series"], list)

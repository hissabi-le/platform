import asyncio
import os

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test"

from api.src.main import app
from api.src.database import engine, Base, async_session
from api.src.models import Organisation

import stripe


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    async def init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with async_session() as session:
            session.add(Organisation(name="org"))
            await session.commit()
    asyncio.run(init())


client = TestClient(app)


def test_webhook(monkeypatch):
    def fake_construct_event(payload, sig, secret):
        return {"type": "invoice.paid", "data": {"object": {"id": "sub"}}, "org_id": 1}

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct_event)
    resp = client.post("/webhooks/stripe", data="{}", headers={"stripe-signature": "sig"})
    assert resp.status_code == 200

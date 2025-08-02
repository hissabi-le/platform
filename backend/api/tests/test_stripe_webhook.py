import asyncio
import os

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
pytest.importorskip("stripe")

try:
    from fastapi.testclient import TestClient

    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test"

    from src.main import app
    from src.database import engine, Base, async_session
    from src.models import Organisation

    import stripe
except Exception as exc:  # pragma: no cover - handled via skip
    pytest.skip(f"Required dependencies not installed: {exc}", allow_module_level=True)


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

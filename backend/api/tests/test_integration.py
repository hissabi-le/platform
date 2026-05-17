import os

import pytest
import pytest_asyncio
import json
import asyncio
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from sqlalchemy import select, delete

from src.main import app
from src.security import create_access_token, decode_token, TokenType
from src.models import User, Subscription, Organisation, JournalEntry, Transaction, Upload, Document
from src.tasks.process_upload import _process_upload

# Integration tests require Redis (for Dramatiq enqueue). Skip in environments
# where it isn't configured so contributors can still run unit tests locally.
pytestmark = pytest.mark.skipif(
    not os.getenv("REDIS_URL"),
    reason="Integration tests require REDIS_URL to be set",
)

# -----------------------------------------------------------------------------
# FIXTURES
# -----------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

@pytest_asyncio.fixture
async def test_org(async_db_session):
    # Ensure fresh org for each test
    org = Organisation(name="Integration Test Org")
    async_db_session.add(org)
    await async_db_session.flush()
    return org

@pytest_asyncio.fixture
async def test_user(async_db_session, test_org):
    import uuid
    user = User(
        email=f"test_{uuid.uuid4()}@example.com",
        hashed_password=pwd_context.hash("password"),
        org_id=test_org.id,
        role="admin",
        is_active=True
    )
    async_db_session.add(user)
    
    # Create valid subscription
    sub = Subscription(
        org_id=test_org.id,
        stripe_subscription_id=f"sub_test_{uuid.uuid4()}",
        plan="pro",
        status="active"
    )
    async_db_session.add(sub)
    await async_db_session.commit()
    await async_db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(user=test_user)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def mock_ai_journal():
    with patch("src.routers.journal.assistant_client.parse_journal_lines") as mock:
        yield mock

@pytest.fixture
def mock_ai_upload():
    with patch("src.tasks.process_upload.OpenAIClient") as mock_cls:
        instance = mock_cls.return_value
        instance.client = MagicMock()
        yield instance

# -----------------------------------------------------------------------------
# AUTH TESTS
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auth_flow(client, async_db_session):
    # 1. Register
    import uuid
    email = f"new_user_{uuid.uuid4()}@example.com"
    reg_payload = {
        "email": email,
        "password": "strongpassword",
        "org_name": "New Org"
    }
    resp = client.post("/auth/register", json=reg_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    
    # 2. Login
    login_payload = {
        "email": email,
        "password": "strongpassword"
    }
    resp = client.post("/auth/login", json=login_payload)
    assert resp.status_code == 200
    login_data = resp.json()
    assert "access_token" in login_data
    
    # 3. Access Protected Route
    headers = {"Authorization": f"Bearer {login_data['access_token']}"}
    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == email

    # 4. Refresh Token
    refresh_payload = {"refresh_token": login_data["refresh_token"]}
    resp = client.post("/auth/refresh", json=refresh_payload)
    assert resp.status_code == 200
    assert "access_token" in resp.json()

# -----------------------------------------------------------------------------
# JOURNAL INGESTION TESTS
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_journal_ingestion_hapyy_path(client, auth_headers, mock_ai_journal):
    """Test standard ingestion flow with mocked AI response."""
    raw_text = "Sold 5 coffees for $15"
    
    # Mock AI response
    mock_ai_journal.return_value = {
        "language": "en",
        "entries": [{
            "entry_type": "revenue",
            "item_name": "coffees",
            "total": 15.0,
            "category": "Sales",
            "resolved": True,
            "ambiguous": False
        }]
    }

    payload = {"date": "2023-10-25", "raw_text": raw_text, "commit": True}
    response = client.post("/journal/day", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    assert float(data["journal_day"]["total_revenue"]) == 15.0
    assert len(data["entries"]) == 1
    assert data["entries"][0]["item_name"] == "coffees"


@pytest.mark.asyncio
async def test_journal_ambiguous_entry(client, auth_headers, mock_ai_journal):
    """Test ingestion where AI marks entry as ambiguous."""
    mock_ai_journal.return_value = {
        "language": "en",
        "entries": [{
            "entry_type": "cost",
            "total": 100.0,
            "resolved": False,
            "ambiguous": True,
            "clarification_question": "What is this for?"
        }]
    }
    
    payload = {"date": "2023-10-26", "raw_text": "Spent 100", "commit": True}
    resp = client.post("/journal/day", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["journal_day"]["parse_status"] == "needs_review"
    assert len(data["clarifications"]) == 1
    assert data["clarifications"][0]["question"] == "What is this for?"

    # Resolve it
    clarification = data["clarifications"][0]
    entry_id = clarification["entry_id"]
    day_id = data["journal_day"]["id"]
    
    resolve_payload = {
        "resolutions": [{
            "entry_id": entry_id,
            "category": "Supplies",
            "notes": "Office supplies"
        }]
    }
    
    patch_resp = client.patch(f"/journal/day/{day_id}/resolve", json=resolve_payload, headers=auth_headers)
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    
    # Verify resolution
    assert patch_data["journal_day"]["parse_status"] == "parsed"
    assert len(patch_data["clarifications"]) == 0
    resolved_entry = next(e for e in patch_data["entries"] if e["id"] == entry_id)
    assert resolved_entry["resolved"] is True
    assert resolved_entry["category"] == "Supplies"

# -----------------------------------------------------------------------------
# ANALYTICS TESTS
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analytics_aggregation(client, auth_headers, async_db_session, test_user):
    """Verify that adding journal entries updates the P&L."""
    
    # Clean slate for this org
    await async_db_session.execute(delete(JournalEntry).where(JournalEntry.org_id == test_user.org_id))
    
    # Direct DB injection to speed up test (avoiding API overhead for setup)
    # 1. Add Revenue
    rev = JournalEntry(
        org_id=test_user.org_id,
        journal_day_id=1, # Mock ID, we need a JournalDay first actually
        entry_type="revenue",
        total=1000.0,
        payment_status="paid",
        created_at=datetime.now(timezone.utc)
    )
    # We need a parent JournalDay
    from src.models import JournalDay
    day = JournalDay(
        org_id=test_user.org_id,
        user_id=test_user.id,
        journal_date=datetime.now(timezone.utc).date(),
        raw_text="Manual seed",
        hash_key="seed_123",
        parse_status="parsed"
    )
    async_db_session.add(day)
    await async_db_session.flush()
    rev.journal_day_id = day.id
    async_db_session.add(rev)
    
    # 2. Add Expense
    exp = JournalEntry(
        org_id=test_user.org_id,
        journal_day_id=day.id,
        entry_type="cost",
        total=200.0,
        payment_status="paid",
        created_at=datetime.now(timezone.utc)
    )
    async_db_session.add(exp)
    await async_db_session.commit()
    
    # 3. Check Analytics P&L
    resp = client.get("/analytics/pnl?range=3m", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    
    # Check Aggregates
    # Expected: Revenue 1000, Expense 200, Profit 800
    assert data["revenue"] == 1000.0
    assert data["expenses"] == 200.0
    assert data["profit"] == 800.0

# -----------------------------------------------------------------------------
# UPLOAD FLOW TEST
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_document_upload_processing(client, auth_headers, async_db_session, test_user, mock_ai_upload):
    """Test full upload flow: Upload API -> Task Processing -> Transaction Creation."""
    
    # 1. Upload File
    files = {"file": ("bank_statement.csv", b"Date,Description,Amount\n2023-01-01,Salary,-5000\n", "text/csv")}
    resp = client.post("/uploads", files=files, headers=auth_headers)
    assert resp.status_code == 202
    data = resp.json()
    upload_id = data["id"]
    document_id = data["document_id"]
    
    # 2. Mock AI to return a Transaction List from this content
    # The worker calls `_ai_ingest_document`
    # We mock the response of the LLM call inside `_ai_ingest_document`
    # But `_process_upload` logic calls `_ai_ingest_document(raw_df)`.
    # We can patch `src.tasks.process_upload._ai_ingest_document` directly.
    
    with patch("src.tasks.process_upload._ai_ingest_document") as mock_ingest:
        mock_ingest.return_value = [{
            "date": datetime(2023, 1, 1),
            "description": "Salary",
            "amount": -5000.0,
            "category": "Salaries",
            "currency": "USD",
            "payment_status": "paid",
            "is_inventory": False,
            "item_name": None
        }]
        
        # 3. Manually trigger the background task
        # We need the storage path. The API created it.
        # We can query the DB to get the path
        doc = await async_db_session.get(Document, document_id)
        assert doc is not None
        storage_path = doc.storage_path
        
        # Run process
        await _process_upload(upload_id, test_user.org_id, storage_path)
        
    # 4. Verify Transaction Exists in DB
    result = await async_db_session.execute(
        select(Transaction).where(Transaction.upload_id == upload_id)
    )
    txns = result.scalars().all()
    assert len(txns) == 1
    assert txns[0].amount == -5000.0
    assert txns[0].category == "Salaries"

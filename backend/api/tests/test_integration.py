import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch
from passlib.context import CryptContext
from datetime import datetime
from src.main import app
from src.security import create_access_token
from src.models import User, Subscription

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

@pytest_asyncio.fixture
async def test_user(async_db_session):
    # Create organisation
    from src.models import Organisation
    org = Organisation(name="Test Org")
    async_db_session.add(org)
    await async_db_session.flush()  # get ID
    
    # Create test user
    user = User(
        email="test@example.com",
        hashed_password=pwd_context.hash("password"),
        org_id=org.id,
        role="admin",
        is_active=True
    )
    async_db_session.add(user)
    
    # Create subscription
    sub = Subscription(
        org_id=org.id,
        stripe_subscription_id="sub_123",
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
def mock_analyze_journal():
    with patch("src.routers.journal.assistant_client.parse_journal_lines") as mock:
        yield mock

@pytest.mark.asyncio
async def test_journal_ingestion_end_to_end(client, auth_headers, mock_analyze_journal):
    """
    Test the full flow:
    1. User submits raw journal text.
    2. System (mocked AI) parses it into structured data.
    3. API persists it to the DB.
    4. API returns the structured result.
    """
    
    # 1. Setup the mock to return what the AI *would* return
    raw_text = "Sold 5 coffees for $15\nPaid $50 for electricity"
    
    mock_analyze_journal.return_value = {
        "language": "en",
        "entries": [
            {
                "entry_type": "revenue",
                "item_name": "coffees",
                "quantity": 5,
                "unit": "cup",
                "unit_cost": 3.0,
                "total": 15.0,
                "category": "Sales",
                "vat_percent": None,
                "vat_included": None,
                "notes": None,
                "ambiguous": False,
                "clarification_question": None,
                "resolved": True
            },
            {
                "entry_type": "cost",
                "item_name": "electricity",
                "quantity": None,
                "unit": None,
                "unit_cost": None,
                "total": 50.0,
                "category": "Utilities",
                "vat_percent": None,
                "vat_included": None,
                "notes": None,
                "ambiguous": False,
                "clarification_question": None,
                "resolved": True
            }
        ]
    }

    # 2. Make the request
    payload = {
        "date": "2023-10-25",
        "raw_text": raw_text,
        "commit": True
    }
    
    response = client.post("/journal/day", json=payload, headers=auth_headers)
    
    # 3. Verify Response
    assert response.status_code == 200, f"Response: {response.text}"
    data = response.json()
    
    assert data["journal_day"]["journal_date"] == "2023-10-25"
    assert float(data["journal_day"]["total_revenue"]) == 15.0
    assert float(data["journal_day"]["total_cost"]) == 50.0
    assert float(data["journal_day"]["net_profit"]) == -35.0
    
    # Verify entries in response
    entries = data["entries"]
    assert len(entries) == 2
    
    rev = next(e for e in entries if e["entry_type"] == "revenue")
    assert rev["item_name"] == "coffees"
    assert float(rev["total"]) == 15.0
    
    cost = next(e for e in entries if e["entry_type"] == "cost")
    assert cost["item_name"] == "electricity"
    assert float(cost["total"]) == 50.0

    # 4. Verify DB State (via GET request)
    get_resp = client.get("/journal/day?date_str=2023-10-25", headers=auth_headers)
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert float(get_data["journal_day"]["net_profit"]) == -35.0
    assert len(get_data["entries"]) == 2

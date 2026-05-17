# src/routers/personal.py
"""API endpoints for Hisabi Personal - personal expense/income tracking."""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..cache.spend_cap_cache import spend_cap_cache
from ..database import get_db
from ..models import PersonalCategory, PersonalEntryType
from ..repositories.personal import PersonalRepo, assert_user_in_org
from ..security import AuthContext, require_plan
from ..assistant import OpenAIClient


async def personal_auth(
    auth: AuthContext = Depends(require_plan("personal")),
    session: AsyncSession = Depends(get_db),
) -> AuthContext:
    """Auth + tenant-isolation tripwire for personal routes.

    ``security.current_user`` already verifies that the JWT's ``org`` claim
    matches the User row's current ``org_id``. This dependency re-runs that
    check explicitly on every personal request — defense-in-depth against
    a stale cache or a User row that has been re-orged since the token was
    issued. Personal repository methods stay keyed by ``user_id`` only,
    because the data model is per-user; org-level tenancy is enforced at
    this boundary instead of in every query.
    """
    await assert_user_in_org(session, auth.user.id, auth.user.org_id)
    return auth

router = APIRouter(prefix="/personal", tags=["personal"])
personal_repo = PersonalRepo()
openai_client = OpenAIClient()


# ==================== Schemas ====================

class PersonalEntryCreate(BaseModel):
    """Request schema for creating a personal entry."""
    entry_date: date
    entry_type: str = Field(..., pattern="^(income|expense)$")
    category: str
    amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    description: Optional[str] = None
    vendor: Optional[str] = None
    notes: Optional[str] = None


class PersonalEntryUpdate(BaseModel):
    """Request schema for updating a personal entry."""
    entry_date: Optional[date] = None
    entry_type: Optional[str] = Field(None, pattern="^(income|expense)$")
    category: Optional[str] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = None
    description: Optional[str] = None
    vendor: Optional[str] = None
    notes: Optional[str] = None


class PersonalEntryResponse(BaseModel):
    """Response schema for a personal entry."""
    id: int
    entry_date: date
    entry_type: str
    category: str
    amount: float
    currency: str
    description: Optional[str]
    vendor: Optional[str]
    notes: Optional[str]
    ai_categorized: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ParseTextRequest(BaseModel):
    """Request for AI text parsing."""
    text: str = Field(..., min_length=3, max_length=2000)
    default_date: Optional[date] = None


class ParsedEntry(BaseModel):
    """Parsed entry from AI."""
    entry_type: str
    category: str
    amount: float
    description: str
    vendor: Optional[str] = None
    entry_date: Optional[date] = None


class BudgetCreate(BaseModel):
    """Request for creating/updating a budget."""
    category: str
    monthly_limit: Decimal = Field(..., gt=0)


class BudgetResponse(BaseModel):
    """Budget response."""
    id: int
    category: str
    monthly_limit: float

    class Config:
        from_attributes = True


class BudgetProgressResponse(BaseModel):
    """Budget with progress info."""
    category: str
    monthly_limit: float
    spent: float
    remaining: float
    percent_used: float


class ChatRequest(BaseModel):
    """Request for AI chat."""
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    """AI chat response."""
    response: str
    insights: Optional[dict] = None


class PersonalAccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    balance: Decimal = Field(default=0)
    type: str = Field(default="checking", min_length=1, max_length=50)


class PersonalAccountResponse(BaseModel):
    id: int
    name: str
    balance: float
    type: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Entries Endpoints ====================

@router.post("/entries", response_model=PersonalEntryResponse)
async def create_entry(
    payload: PersonalEntryCreate,
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Create a new personal finance entry."""
    entry = await personal_repo.create_entry(
        session=session,
        user_id=auth.user.id,
        entry_date=payload.entry_date,
        entry_type=payload.entry_type,
        category=payload.category,
        amount=payload.amount,
        currency=payload.currency,
        description=payload.description,
        vendor=payload.vendor,
        notes=payload.notes,
    )
    await session.commit()
    return entry


@router.get("/entries", response_model=List[PersonalEntryResponse])
async def list_entries(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
    entry_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """List personal entries with filters."""
    entries = await personal_repo.list_entries(
        session=session,
        user_id=auth.user.id,
        start_date=start_date,
        end_date=end_date,
        category=category,
        entry_type=entry_type,
        limit=limit,
        offset=offset,
    )
    return entries


@router.get("/entries/{entry_id}", response_model=PersonalEntryResponse)
async def get_entry(
    entry_id: int,
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Get a single entry by ID."""
    entry = await personal_repo.get_entry_by_id(session, auth.user.id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.put("/entries/{entry_id}", response_model=PersonalEntryResponse)
async def update_entry(
    entry_id: int,
    payload: PersonalEntryUpdate,
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Update a personal entry."""
    entry = await personal_repo.get_entry_by_id(session, auth.user.id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    updates = payload.model_dump(exclude_unset=True)
    entry = await personal_repo.update_entry(session, entry, **updates)
    await session.commit()
    return entry


@router.delete("/entries/{entry_id}")
async def delete_entry(
    entry_id: int,
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Delete a personal entry."""
    entry = await personal_repo.get_entry_by_id(session, auth.user.id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    await personal_repo.delete_entry(session, entry)
    await session.commit()
    return {"ok": True}


# ==================== AI Parsing ====================

PERSONAL_PARSE_PROMPT = """You are a personal finance assistant. Parse the following text and extract expense or income entries.

For each entry, extract:
- entry_type: "income" or "expense"
- amount: numeric value (just the number, no currency symbols)
- category: one of the following categories
- description: brief description of the transaction
- vendor: merchant/source name if mentioned
- entry_date: date in YYYY-MM-DD format if mentioned, otherwise null

CATEGORIES:
Income: salary, freelance, investment_income, other_income
Food & Drink: groceries, dining, delivery, alcohol, nightlife
Lifestyle: fitness, wellness, fashion, entertainment, personal_care
Housing & Bills: rent, utilities, household, subscriptions
Finance: investments, savings
Other: transportation, healthcare, education, travel, gifts, other

Rules:
- Default to "expense" unless it's clearly income (salary, payment received, etc.)
- Be precise with amounts - extract exact numbers
- If vendor/merchant is mentioned, include it
- Return a JSON array of entries

Example input: "Paid $45 for dinner at Olive Garden, then $12 uber home"
Example output: [
  {"entry_type": "expense", "amount": 45, "category": "dining", "description": "Dinner", "vendor": "Olive Garden"},
  {"entry_type": "expense", "amount": 12, "category": "transportation", "description": "Uber ride home", "vendor": "Uber"}
]

Parse the following text:
"""


@router.post("/parse", response_model=List[ParsedEntry])
async def parse_text(
    payload: ParseTextRequest,
    auth: AuthContext = Depends(personal_auth),
):
    """Parse free-text input using AI and extract entries."""
    await spend_cap_cache.check_or_raise(auth.user.org_id)
    try:
        prompt = PERSONAL_PARSE_PROMPT + payload.text
        response = await asyncio.to_thread(openai_client.chat_json, prompt)
        if openai_client.last_total_tokens:
            await spend_cap_cache.record_usage(
                auth.user.org_id, openai_client.last_total_tokens
            )

        if not response:
            return []

        entries = []
        for item in response:
            try:
                amount = float(item.get("amount", 0))
            except (TypeError, ValueError):
                continue
            entry = ParsedEntry(
                entry_type=item.get("entry_type", "expense"),
                category=item.get("category", "other"),
                amount=amount,
                description=item.get("description", ""),
                vendor=item.get("vendor"),
                entry_date=payload.default_date,
            )
            entries.append(entry)

        return entries
    except HTTPException:
        raise
    except Exception:
        # Don't leak internal error detail to clients (P0-6).
        raise HTTPException(status_code=500, detail="Failed to parse text")


@router.post("/parse/save", response_model=List[PersonalEntryResponse])
async def parse_and_save(
    payload: ParseTextRequest,
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Parse text and directly save entries."""
    parsed = await parse_text(payload, auth)
    
    entries = []
    for p in parsed:
        entry = await personal_repo.create_entry(
            session=session,
            user_id=auth.user.id,
            entry_date=p.entry_date or payload.default_date or date.today(),
            entry_type=p.entry_type,
            category=p.category,
            amount=Decimal(str(p.amount)),
            description=p.description,
            vendor=p.vendor,
            ai_categorized=True,
        )
        entries.append(entry)

    await session.commit()
    return entries


# ==================== Analytics Endpoints ====================

@router.get("/analytics/summary")
async def get_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Get spending summary for date range."""
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = date(end_date.year, end_date.month, 1)  # Month start

    summary = await personal_repo.get_summary(
        session, auth.user.id, start_date, end_date
    )
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "income": float(summary["income"]),
        "expense": float(summary["expense"]),
        "net": float(summary["net"]),
    }


@router.get("/analytics/by-category")
async def get_category_breakdown(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    entry_type: str = "expense",
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Get spending breakdown by category (pie chart data)."""
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = date(end_date.year, end_date.month, 1)

    breakdown = await personal_repo.get_category_breakdown(
        session, auth.user.id, start_date, end_date, entry_type
    )
    return {"breakdown": breakdown}


@router.get("/analytics/trends")
async def get_trends(
    months: int = 12,
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Get monthly income/expense trends (bar chart data)."""
    trends = await personal_repo.get_monthly_trends(session, auth.user.id, months)
    return {"trends": trends}


@router.get("/analytics/top-spending")
async def get_top_spending(
    days: int = 30,
    category: Optional[str] = None,
    limit: int = 5,
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Get top spending items with time/category filter."""
    items = await personal_repo.get_top_spending(
        session, auth.user.id, days, category, limit
    )
    return {"days": days, "category": category, "items": items}


@router.get("/insights")
async def get_insights(
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Get personalized insights for greeting message."""
    insights = await personal_repo.get_insights(session, auth.user.id)
    return insights


# ==================== Accounts Endpoints ====================

@router.get("/accounts", response_model=List[PersonalAccountResponse])
async def list_accounts(
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """List all personal accounts."""
    return await personal_repo.list_accounts(session, auth.user.id)


@router.post("/accounts", response_model=PersonalAccountResponse)
async def create_account(
    payload: PersonalAccountCreate,
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Create a new personal account."""
    account = await personal_repo.create_account(
        session, auth.user.id, payload.name, payload.balance, payload.type
    )
    await session.commit()
    return account


@router.delete("/accounts/{account_id}")
async def delete_account(
    account_id: int,
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Delete a personal account."""
    account = await personal_repo.get_account(session, auth.user.id, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    await personal_repo.delete_account(session, account)
    await session.commit()
    return {"ok": True}


# ==================== Budget Endpoints ====================

@router.get("/budgets", response_model=List[BudgetResponse])
async def list_budgets(
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """List all budgets for the user."""
    budgets = await personal_repo.list_budgets(session, auth.user.id)
    return budgets


@router.post("/budgets", response_model=BudgetResponse)
async def create_or_update_budget(
    payload: BudgetCreate,
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Create or update a budget for a category."""
    budget = await personal_repo.upsert_budget(
        session, auth.user.id, payload.category, payload.monthly_limit
    )
    await session.commit()
    return budget


@router.delete("/budgets/{category}")
async def delete_budget(
    category: str,
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Delete a budget for a category."""
    budget = await personal_repo.get_budget_by_category(session, auth.user.id, category)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    await personal_repo.delete_budget(session, budget)
    await session.commit()
    return {"ok": True}


@router.get("/budgets/progress", response_model=List[BudgetProgressResponse])
async def get_budget_progress(
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Get all budgets with current month spending progress."""
    progress = await personal_repo.get_budget_progress(session, auth.user.id)
    return progress


# ==================== AI Chat ====================

PERSONAL_CHAT_PROMPT = """You are a friendly, knowledgeable personal finance assistant for the Hisabi app.
You have full access to the user's financial data below. Answer questions accurately using the numbers provided.
Be conversational, supportive, and give actionable advice. Keep responses concise but helpful.

=== USER'S FINANCIAL SNAPSHOT ===

THIS MONTH:
  Income: ${this_month_income:.0f}
  Expenses: ${this_month_expense:.0f}
  Net: ${this_month_net:.0f}

THIS WEEK:
  Income: ${this_week_income:.0f}
  Expenses: ${this_week_expense:.0f}

TOP 5 SPENDING CATEGORIES (this month):
{top5_categories}

BUDGET STATUS:
{budget_status}

MONTHLY TRENDS (last 3 months):
{monthly_trends}

RECENT TRANSACTIONS (last 10):
{recent_transactions}

=== END SNAPSHOT ===

User's message: {message}
"""


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Chat with AI about personal finances."""
    # Get rich financial context
    ctx = await personal_repo.get_chat_context(session, auth.user.id)

    prompt = PERSONAL_CHAT_PROMPT.format(
        this_month_income=ctx["this_month_income"],
        this_month_expense=ctx["this_month_expense"],
        this_month_net=ctx["this_month_net"],
        this_week_income=ctx["this_week_income"],
        this_week_expense=ctx["this_week_expense"],
        top5_categories=ctx["top5_categories"],
        budget_status=ctx["budget_status"],
        monthly_trends=ctx["monthly_trends"],
        recent_transactions=ctx["recent_transactions"],
        message=payload.message,
    )

    # Also get basic insights for the response payload
    insights = await personal_repo.get_insights(session, auth.user.id)

    await spend_cap_cache.check_or_raise(auth.user.org_id)
    try:
        # Off-load blocking OpenAI HTTP to a thread (P0-8).
        response = await asyncio.to_thread(openai_client.chat, prompt)
        if openai_client.last_total_tokens:
            await spend_cap_cache.record_usage(
                auth.user.org_id, openai_client.last_total_tokens
            )
        return ChatResponse(response=response, insights=insights)
    except HTTPException:
        raise
    except Exception:
        # Don't leak internal error detail to clients (P0-6).
        raise HTTPException(status_code=500, detail="Chat failed")


@router.get("/categories")
async def list_categories():
    """List all available personal categories."""
    categories = {
        "income": ["salary", "freelance", "investment_income", "other_income"],
        "food_drink": ["groceries", "dining", "delivery", "alcohol", "nightlife"],
        "lifestyle": ["fitness", "wellness", "fashion", "entertainment", "personal_care"],
        "housing_bills": ["rent", "utilities", "household", "subscriptions"],
        "finance": ["investments", "savings"],
        "other": ["transportation", "healthcare", "education", "travel", "gifts", "other"],
    }
    return categories


# ==================== The Flow (Sankey) ====================

@router.get("/analytics/flow")
async def get_flow_data(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Get Sankey diagram data showing money flow: Income → Category → Merchant."""
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = date(end_date.year, end_date.month, 1)

    flow_data = await personal_repo.get_flow_data(
        session, auth.user.id, start_date, end_date
    )
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        **flow_data,
    }


# ==================== Merchant DNA ====================

@router.get("/merchants")
async def get_top_merchants(
    limit: int = 10,
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Get top merchants by total spend."""
    merchants = await personal_repo.get_top_merchants(session, auth.user.id, limit)
    return {"merchants": merchants}


@router.get("/merchants/{vendor}")
async def get_merchant_profile(
    vendor: str,
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Get detailed profile for a specific merchant (Merchant DNA)."""
    profile = await personal_repo.get_merchant_profile(session, auth.user.id, vendor)
    if not profile:
        raise HTTPException(status_code=404, detail="No transactions found for this merchant")
    return profile


# ==================== WhatsApp Integration ====================

class WhatsAppLinkRequest(BaseModel):
    """Request to link a WhatsApp number."""
    phone_number: str = Field(..., min_length=10, max_length=20,
                              description="Phone number in E.164 format (e.g. +1234567890)")


@router.post("/settings/whatsapp/link")
async def link_whatsapp(
    payload: WhatsAppLinkRequest,
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """
    Link a WhatsApp number to the user's account.
    Sends a 6-digit OTP via WhatsApp for verification.
    """
    import re
    import secrets

    # Normalize phone number to E.164
    phone = payload.phone_number.strip()
    if not phone.startswith("+"):
        phone = "+" + phone
    if not re.match(r"^\+[1-9]\d{6,14}$", phone):
        raise HTTPException(status_code=400, detail="Invalid phone number format. Use E.164 (e.g. +1234567890)")

    # Check if another user already has this number
    from sqlalchemy import select
    from ..models import User
    existing = await session.scalar(
        select(User).where(User.phone_number == phone, User.id != auth.user.id)
    )
    if existing:
        raise HTTPException(status_code=409, detail="This phone number is already linked to another account")

    # Generate 6-digit OTP
    otp = "{:06d}".format(secrets.randbelow(1000000))

    # Store OTP in Redis (10 minute TTL)
    from ..config import settings
    if settings.redis_url:
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.redis_url, decode_responses=True)
            await r.set(f"wa_otp:{auth.user.id}", otp, ex=600)
            await r.aclose()
        except Exception as e:
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    else:
        raise HTTPException(status_code=503, detail="Redis not configured")

    # Update user's phone number (unverified)
    auth.user.phone_number = phone
    auth.user.whatsapp_verified = False
    await session.commit()

    # Send OTP via WhatsApp
    from ..whatsapp_client import send_whatsapp_message
    sent = await send_whatsapp_message(
        phone,
        f"🔐 Your Hissabi verification code is: *{otp}*\n\n"
        f"Reply with this code to verify your WhatsApp number.\n"
        f"This code expires in 10 minutes."
    )

    if not sent:
        return {"status": "pending", "message": "Phone saved but OTP delivery failed. Check Twilio config."}

    return {"status": "otp_sent", "message": "Verification code sent to your WhatsApp"}


@router.post("/settings/whatsapp/unlink")
async def unlink_whatsapp(
    auth: AuthContext = Depends(personal_auth),
    session: AsyncSession = Depends(get_db),
):
    """Unlink WhatsApp from the user's account."""
    auth.user.phone_number = None
    auth.user.whatsapp_verified = False
    auth.user.whatsapp_opt_in = False
    await session.commit()
    return {"ok": True}


@router.get("/settings/whatsapp/status")
async def whatsapp_status(
    auth: AuthContext = Depends(personal_auth),
):
    """Get WhatsApp linking status."""
    return {
        "linked": auth.user.phone_number is not None,
        "verified": auth.user.whatsapp_verified,
        "phone": auth.user.phone_number,
    }

    return {
        "linked": auth.user.phone_number is not None,
        "verified": auth.user.whatsapp_verified,
        "phone": auth.user.phone_number,
    }

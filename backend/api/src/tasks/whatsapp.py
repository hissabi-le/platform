"""
WhatsApp message processor — Dramatiq actor.

Processing order (deterministic checks first, LLM last):
1. Unlinked user?        → "Link your account at hissabi.com"
2. Pending OTP?          → Direct string compare (no LLM)
3. Pending clarification? → Validate reply shape, concatenate or abandon
4. classify_intent (LLM) → LOG_TRANSACTION / QUERY_DATA / GREETING

Critical design decisions (from architectural review):
- OTP verification is DETERMINISTIC — never hits the LLM
- Clarification race condition guard — checks if reply looks like a direct answer
- Top-level try/except — always sends a fallback message on crash
- wa_history only stores QUERY_DATA pairs to prevent LLM re-logging
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import date
from decimal import Decimal
from typing import Any, Optional

import dramatiq

from ..assistant import OpenAIClient
from ..config import settings
from ..database import async_session
from ..models import User
from ..repositories.personal import PersonalRepo
from ..whatsapp_client import send_whatsapp_message

log = logging.getLogger(__name__)

personal_repo = PersonalRepo()

# ---------------------------------------------------------------------------
# Intent classification prompt (cheap, fast — gpt-4o-mini)
# ---------------------------------------------------------------------------

INTENT_SYSTEM_PROMPT = """You classify WhatsApp messages for a personal finance app.

Respond with EXACTLY one word — no explanation, no punctuation:

LOG_TRANSACTION — if the user is logging an expense, income, purchase, or payment.
  Examples: "paid 20$ for dinner", "got my salary 3000$", "bought shoes for 90$", "uber 12$"

QUERY_DATA — if the user is asking a question about their finances.
  Examples: "how much did I spend this month?", "what's my balance?", "show me my spending"

GREETING — if the user is saying hello, thanks, or anything conversational.
  Examples: "hi", "hello", "thanks", "hey hissabi", "what can you do?"

Respond with exactly one of: LOG_TRANSACTION, QUERY_DATA, GREETING"""

# ---------------------------------------------------------------------------
# Personal parse prompt (reused from routers/personal.py)
# ---------------------------------------------------------------------------

PERSONAL_PARSE_PROMPT = """You are a personal finance assistant. Parse the following text and extract expense or income entries.

For each entry, extract:
- entry_type: "income" or "expense"
- amount: numeric value (just the number, no currency symbols)
- category: one of the following categories
- description: brief description of the transaction
- vendor: merchant/source name if mentioned

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

Output format: [{"entry_type": "expense", "amount": 45, "category": "dining", "description": "Dinner", "vendor": "Olive Garden"}]

Parse the following text:
"""

# ---------------------------------------------------------------------------
# Chat prompt (reused from routers/personal.py)
# ---------------------------------------------------------------------------

PERSONAL_CHAT_PROMPT = """You are a friendly, knowledgeable personal finance assistant for the Hisabi app.
You have full access to the user's financial data below. Answer questions accurately using the numbers provided.
Be conversational, supportive, and give actionable advice. Keep responses concise but helpful.
You are replying via WhatsApp, so keep it brief and use emojis where appropriate.

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

User's message: {message}"""


# ---------------------------------------------------------------------------
# Redis helpers
# ---------------------------------------------------------------------------

async def _get_redis():
    try:
        import redis.asyncio as aioredis
        if settings.redis_url:
            return aioredis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Clarification reply detector
# ---------------------------------------------------------------------------

def _looks_like_direct_answer(text: str) -> bool:
    """
    Check if text looks like a direct answer to a clarification question
    (e.g., "$50", "50", "50 dollars") rather than a new transaction.

    Heuristic: short text (<30 chars) that is primarily numeric/currency.
    """
    stripped = text.strip()
    if len(stripped) > 40:
        return False
    # Remove currency symbols and whitespace for analysis
    cleaned = re.sub(r"[\$€£¥,\s]", "", stripped)
    # Check if what remains is mostly numeric
    digits = sum(1 for c in cleaned if c.isdigit() or c == ".")
    return len(cleaned) > 0 and digits / len(cleaned) >= 0.5


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

def _classify_intent(llm: OpenAIClient, text: str) -> str:
    """Classify user intent. Returns LOG_TRANSACTION, QUERY_DATA, or GREETING."""
    if not llm.client:
        # Fallback heuristic when LLM is unavailable
        lower = text.lower()
        question_words = {"how", "what", "when", "where", "show", "tell", "which", "?"}
        if any(w in lower for w in question_words):
            return "QUERY_DATA"
        greeting_words = {"hi", "hello", "hey", "thanks", "thank", "sup", "yo"}
        if any(lower.startswith(w) for w in greeting_words):
            return "GREETING"
        return "LOG_TRANSACTION"

    try:
        comp = llm.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            max_tokens=10,
            temperature=0,
            timeout=10,
        )
        result = (comp.choices[0].message.content or "").strip().upper()
        if result in ("LOG_TRANSACTION", "QUERY_DATA", "GREETING"):
            return result
        log.warning("Unexpected intent classification: %s", result)
        return "LOG_TRANSACTION"  # Default to logging
    except Exception:
        log.exception("Intent classification failed")
        return "LOG_TRANSACTION"


# ---------------------------------------------------------------------------
# Transaction parser
# ---------------------------------------------------------------------------

def _parse_transaction(llm: OpenAIClient, text: str) -> list[dict[str, Any]]:
    """Parse transaction text into structured entries."""
    if not llm.client:
        return []

    try:
        prompt = PERSONAL_PARSE_PROMPT + text
        comp = llm.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            timeout=15,
        )
        raw = comp.choices[0].message.content or "[]"
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Handle {"entries": [...]} or {"items": [...]} wrapper
            return data.get("entries", data.get("items", [data]))
        return []
    except Exception:
        log.exception("Transaction parsing failed")
        return []


# ---------------------------------------------------------------------------
# Dramatiq Actor
# ---------------------------------------------------------------------------

@dramatiq.actor(max_retries=0, queue_name="whatsapp")
def process_whatsapp_message(sender_number: str, text: str, message_sid: str = "") -> None:
    """Entry point — Dramatiq runs this synchronously, we bridge to async."""
    asyncio.run(_process_message(sender_number, text, message_sid))


async def _process_message(sender_number: str, text: str, message_sid: str) -> None:
    """
    Core message processing pipeline.
    Wrapped in top-level try/except — always sends a fallback on crash.
    """
    try:
        await _process_message_inner(sender_number, text, message_sid)
    except Exception:
        log.exception("Unhandled error processing WhatsApp message from %s", sender_number)
        # Fail-safe: always tell the user something
        await send_whatsapp_message(
            sender_number,
            "Sorry, I'm having trouble right now. Please try again in a moment. 🔧"
        )


async def _process_message_inner(sender_number: str, text: str, message_sid: str) -> None:
    """Inner processing — may raise; outer wrapper handles errors."""
    async with async_session() as db:
        # ---------------------------------------------------------------
        # 1. Look up user by phone number
        # ---------------------------------------------------------------
        from sqlalchemy import select
        user = await db.scalar(
            select(User).where(
                User.phone_number == sender_number,
            )
        )

        if not user:
            await send_whatsapp_message(
                sender_number,
                "👋 Hi! I don't recognize this number.\n\n"
                "To use Hissabi via WhatsApp, link your phone number "
                "in the app: Settings → WhatsApp Integration.\n\n"
                "Don't have an account? Sign up at hissabi.com"
            )
            return

        if not user.whatsapp_verified:
            # Check if this is an OTP attempt for an unverified user
            redis = await _get_redis()
            if redis:
                try:
                    otp = await redis.get(f"wa_otp:{user.id}")
                    if otp and text.strip() == otp:
                        user.whatsapp_verified = True
                        user.whatsapp_opt_in = True
                        await db.commit()
                        await redis.delete(f"wa_otp:{user.id}")
                        await send_whatsapp_message(
                            sender_number,
                            "✅ Account verified! You can now log expenses and ask "
                            "questions about your finances right here.\n\n"
                            "Try: \"Paid $20 for lunch\" or \"How much did I spend this week?\""
                        )
                        return
                    elif otp:
                        await send_whatsapp_message(
                            sender_number,
                            "❌ Invalid code. Please check the OTP and try again."
                        )
                        return
                finally:
                    await redis.aclose()

            await send_whatsapp_message(
                sender_number,
                "Your phone number isn't verified yet. "
                "Please complete the verification in the Hissabi app: "
                "Settings → WhatsApp Integration."
            )
            return

        # ---------------------------------------------------------------
        # 2. Deterministic OTP check (before LLM)
        # ---------------------------------------------------------------
        redis = await _get_redis()
        if redis:
            try:
                otp = await redis.get(f"wa_otp:{user.id}")
                if otp:
                    if text.strip() == otp:
                        await redis.delete(f"wa_otp:{user.id}")
                        await send_whatsapp_message(sender_number, "✅ Verification confirmed!")
                    else:
                        await send_whatsapp_message(sender_number, "❌ Invalid OTP. Try again.")
                    return
            finally:
                await redis.aclose()

        # ---------------------------------------------------------------
        # 3. Check for pending clarification
        # ---------------------------------------------------------------
        redis = await _get_redis()
        clarification_data = None
        if redis:
            try:
                raw = await redis.get(f"wa_clarification:{user.id}")
                if raw:
                    clarification_data = json.loads(raw)
            finally:
                await redis.aclose()

        if clarification_data:
            if _looks_like_direct_answer(text):
                # Concatenate original text with the answer and re-parse
                original_text = clarification_data.get("original_text", "")
                combined = f"{original_text}. {text}"
                log.info("Clarification reply from user %s: combining '%s' + '%s'",
                         user.id, original_text, text)

                # Clear the clarification state
                redis = await _get_redis()
                if redis:
                    try:
                        await redis.delete(f"wa_clarification:{user.id}")
                    finally:
                        await redis.aclose()

                # Re-parse the combined text
                await _handle_log_transaction(db, user, sender_number, combined)
                return
            else:
                # Doesn't look like a direct answer — abandon clarification
                log.info("Abandoning clarification for user %s — new message: '%s'",
                         user.id, text[:50])
                redis = await _get_redis()
                if redis:
                    try:
                        await redis.delete(f"wa_clarification:{user.id}")
                    finally:
                        await redis.aclose()
                # Fall through to normal classification

        # ---------------------------------------------------------------
        # 4. Classify intent via LLM
        # ---------------------------------------------------------------
        llm = OpenAIClient()
        intent = _classify_intent(llm, text)
        log.info("Intent for user %s: %s (text: '%s')", user.id, intent, text[:80])

        if intent == "LOG_TRANSACTION":
            await _handle_log_transaction(db, user, sender_number, text)
        elif intent == "QUERY_DATA":
            await _handle_query(db, user, sender_number, text)
        else:  # GREETING
            await _handle_greeting(sender_number)


# ---------------------------------------------------------------------------
# Intent handlers
# ---------------------------------------------------------------------------

async def _handle_log_transaction(
    db, user: User, sender_number: str, text: str
) -> None:
    """Parse text and create personal entries."""
    llm = OpenAIClient()
    entries = _parse_transaction(llm, text)

    if not entries:
        await send_whatsapp_message(
            sender_number,
            "I couldn't understand that transaction. "
            "Try something like: \"Paid $20 for dinner\" or \"Got salary $3000\""
        )
        return

    saved_count = 0
    ambiguous_entries = []

    for entry_data in entries:
        amount = entry_data.get("amount")
        if amount is None or amount == 0:
            ambiguous_entries.append(entry_data)
            continue

        try:
            entry = await personal_repo.create_entry(
                session=db,
                user_id=user.id,
                entry_date=date.today(),
                entry_type=entry_data.get("entry_type", "expense"),
                category=entry_data.get("category", "other"),
                amount=Decimal(str(abs(amount))),
                description=entry_data.get("description"),
                vendor=entry_data.get("vendor"),
                ai_categorized=True,
            )
            saved_count += 1
        except Exception:
            log.exception("Failed to save entry for user %s", user.id)

    if saved_count > 0:
        await db.commit()

    # Build response
    if saved_count > 0 and not ambiguous_entries:
        # All entries saved successfully
        if saved_count == 1:
            e = entries[0]
            cat_emoji = _category_emoji(e.get("category", ""))
            msg = (
                f"✅ Logged {e.get('entry_type', 'expense')}: "
                f"{e.get('description', 'Item')} — ${abs(e.get('amount', 0)):.0f} "
                f"{cat_emoji} ({e.get('category', 'other')})"
            )
        else:
            total = sum(abs(e.get("amount", 0)) for e in entries)
            msg = f"✅ Logged {saved_count} entries — total ${total:.0f}"
        await send_whatsapp_message(sender_number, msg)

    elif ambiguous_entries:
        # Some entries need clarification
        first_ambiguous = ambiguous_entries[0]
        question = f"How much did you pay for {first_ambiguous.get('description', 'that')}?"

        # Store clarification state in Redis
        redis = await _get_redis()
        if redis:
            try:
                await redis.set(
                    f"wa_clarification:{user.id}",
                    json.dumps({"original_text": text, "entry_data": first_ambiguous}),
                    ex=3600,
                )
            finally:
                await redis.aclose()

        if saved_count > 0:
            msg = f"✅ Logged {saved_count} entries.\n\n❓ {question}"
        else:
            msg = f"❓ {question}"
        await send_whatsapp_message(sender_number, msg)

    else:
        await send_whatsapp_message(
            sender_number,
            "I couldn't parse that transaction. "
            "Try: \"Paid $20 for dinner\" or \"Got salary $3000\""
        )


async def _handle_query(db, user: User, sender_number: str, text: str) -> None:
    """Answer a question about the user's finances."""
    ctx = await personal_repo.get_chat_context(db, user.id)

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
        message=text,
    )

    llm = OpenAIClient()
    response = llm.chat(prompt)

    await send_whatsapp_message(sender_number, response)

    # Store in query history (QUERY_DATA only — never LOG_TRANSACTION)
    redis = await _get_redis()
    if redis:
        try:
            history_key = f"wa_history:{user.id}"
            pair = json.dumps({"user": text, "assistant": response})
            await redis.lpush(history_key, pair)
            await redis.ltrim(history_key, 0, 4)  # Keep last 5 pairs
            await redis.expire(history_key, 86400)  # 24h TTL
        except Exception:
            log.warning("Failed to store query history")
        finally:
            await redis.aclose()


async def _handle_greeting(sender_number: str) -> None:
    """Send a welcome/help message."""
    await send_whatsapp_message(
        sender_number,
        "👋 Hey! I'm your Hissabi assistant.\n\n"
        "📝 *Log expenses:*\n"
        "\"Paid $20 for dinner\"\n"
        "\"Bought Nike shoes for $90\"\n"
        "\"Got salary $3000\"\n\n"
        "📊 *Ask questions:*\n"
        "\"How much did I spend this week?\"\n"
        "\"What's my top spending category?\"\n\n"
        "Just text me anytime! 💬"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _category_emoji(category: str) -> str:
    """Return an emoji for a spending category."""
    emojis = {
        "dining": "🍽️",
        "groceries": "🛒",
        "transportation": "🚗",
        "entertainment": "🎬",
        "fashion": "👕",
        "fitness": "💪",
        "healthcare": "🏥",
        "education": "📚",
        "travel": "✈️",
        "rent": "🏠",
        "utilities": "💡",
        "subscriptions": "📱",
        "salary": "💰",
        "freelance": "💻",
        "investments": "📈",
        "savings": "🏦",
        "gifts": "🎁",
        "delivery": "📦",
        "nightlife": "🌙",
        "alcohol": "🍷",
        "personal_care": "💅",
        "wellness": "🧘",
        "household": "🏡",
    }
    return emojis.get(category, "💰")

"""
WhatsApp webhook receiver.

Critical design decisions (from architectural review):
- ALWAYS returns HTTP 200 to Twilio (non-2xx triggers 72-hour retries)
- Reads raw body FIRST for HMAC signature validation before parsing form data
- MessageSid idempotency via Redis NX
- Rate limiting drops silently (still 200)
- Non-text payloads (images, voice) get a friendly "text only" reply
"""
from __future__ import annotations

import logging
from urllib.parse import parse_qs

from fastapi import APIRouter, Request, Response

from ..config import settings
from ..whatsapp_client import send_whatsapp_message, validate_twilio_signature

log = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])


async def _get_redis():
    """Lazy Redis connection."""
    try:
        import redis.asyncio as aioredis
        if settings.redis_url:
            return aioredis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        pass
    return None


async def _is_rate_limited(redis_client, phone: str) -> bool:
    """Sliding window rate limit — returns True if over limit."""
    if not redis_client:
        return False
    key = f"wa_rl:{phone}"
    try:
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, 60)
        return count > settings.whatsapp_rate_limit_per_min
    except Exception:
        log.exception("Rate limit check failed")
        return False


async def _is_duplicate(redis_client, message_sid: str) -> bool:
    """Idempotency check via MessageSid — returns True if already processed."""
    if not redis_client or not message_sid:
        return False
    key = f"wa_msg:{message_sid}"
    try:
        # SET NX returns True if key was set (new), False if already exists
        was_set = await redis_client.set(key, "1", nx=True, ex=86400)
        return not was_set  # duplicate if key already existed
    except Exception:
        log.exception("Idempotency check failed")
        return False


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Twilio sends form-encoded POST when a user messages the WhatsApp bot.

    Always returns 200. Never 4xx/5xx — Twilio retries non-2xx for up to 72h,
    which would amplify traffic spikes rather than mitigating them.
    """
    # ---------------------------------------------------------------
    # 1. Read raw body FIRST (before form parsing consumes the stream)
    # ---------------------------------------------------------------
    raw_body = await request.body()

    # ---------------------------------------------------------------
    # 2. Validate Twilio HMAC-SHA1 signature
    # ---------------------------------------------------------------
    auth_token = settings.twilio_auth_token
    if auth_token:
        signature = request.headers.get("X-Twilio-Signature", "")
        # Reconstruct the full URL Twilio used
        request_url = str(request.url)

        # Parse form params from raw bytes for signature validation
        try:
            parsed = parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)
            params = {k: v[0] for k, v in parsed.items()}
        except Exception:
            log.warning("Failed to parse webhook body")
            return Response(status_code=200)

        if not validate_twilio_signature(request_url, params, signature, auth_token):
            log.warning("Invalid Twilio signature from %s", request.client.host if request.client else "unknown")
            return Response(status_code=200)  # Still 200 — don't leak validation info
    else:
        # No auth token configured — parse body but skip validation (dev mode)
        try:
            parsed = parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)
            params = {k: v[0] for k, v in parsed.items()}
        except Exception:
            log.warning("Failed to parse webhook body")
            return Response(status_code=200)

    # ---------------------------------------------------------------
    # 3. Extract message fields
    # ---------------------------------------------------------------
    sender_number = params.get("From", "").replace("whatsapp:", "")
    message_body = params.get("Body", "").strip()
    message_sid = params.get("MessageSid", "")
    num_media = int(params.get("NumMedia", "0"))

    if not sender_number:
        return Response(status_code=200)

    # ---------------------------------------------------------------
    # 4. Redis checks: idempotency + rate limiting
    # ---------------------------------------------------------------
    redis_client = await _get_redis()
    try:
        # Idempotency — drop if we've already processed this MessageSid
        if await _is_duplicate(redis_client, message_sid):
            log.info("Duplicate message %s — dropping", message_sid)
            return Response(status_code=200)

        # Rate limiting — drop silently (still 200)
        if await _is_rate_limited(redis_client, sender_number):
            log.warning("Rate limited %s", sender_number)
            return Response(status_code=200)
    finally:
        if redis_client:
            await redis_client.aclose()

    # ---------------------------------------------------------------
    # 5. Non-text payload handling (images, voice, location)
    # ---------------------------------------------------------------
    if num_media > 0 or not message_body:
        if sender_number:
            # Fire-and-forget: tell user we only support text
            import asyncio
            asyncio.create_task(
                send_whatsapp_message(
                    sender_number,
                    "I currently only support text messages. "
                    "Receipt scanning is coming soon! 📸"
                )
            )
        return Response(status_code=200)

    # ---------------------------------------------------------------
    # 6. Enqueue to Dramatiq worker for async processing
    # ---------------------------------------------------------------
    try:
        from ..tasks.whatsapp import process_whatsapp_message
        process_whatsapp_message.send(sender_number, message_body, message_sid)
        log.info("Enqueued WhatsApp message from %s (sid=%s)", sender_number, message_sid)
    except Exception:
        log.exception("Failed to enqueue WhatsApp message")

    # ---------------------------------------------------------------
    # 7. Always 200
    # ---------------------------------------------------------------
    return Response(status_code=200)

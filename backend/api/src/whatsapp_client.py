"""
Twilio WhatsApp client — thin wrapper around the REST API.

No SDK dependency. Uses httpx (already installed) for outbound messages
and manual HMAC-SHA1 for inbound webhook signature validation.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from urllib.parse import urlencode

import httpx

from .config import settings

log = logging.getLogger(__name__)

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"
WHATSAPP_MAX_LENGTH = 1600


# ---------------------------------------------------------------------------
# Outbound: send a WhatsApp message via Twilio REST API
# ---------------------------------------------------------------------------

async def send_whatsapp_message(to: str, body: str) -> bool:
    """
    Send a WhatsApp message to *to* (E.164, e.g. "+1234567890").
    Returns True on success, False on failure (never raises).
    """
    sid = settings.twilio_account_sid
    token = settings.twilio_auth_token
    from_number = settings.twilio_whatsapp_number

    if not all([sid, token, from_number]):
        log.warning("Twilio credentials not configured — message not sent")
        return False

    # Ensure whatsapp: prefix
    wa_to = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
    wa_from = (
        f"whatsapp:{from_number}"
        if not from_number.startswith("whatsapp:")
        else from_number
    )

    # Truncate to WhatsApp limit
    truncated_body = body[:WHATSAPP_MAX_LENGTH]

    url = f"{TWILIO_API_BASE}/Accounts/{sid}/Messages.json"
    payload = {
        "From": wa_from,
        "To": wa_to,
        "Body": truncated_body,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                data=payload,
                auth=(sid, token),
                timeout=15.0,
            )
        if resp.status_code in (200, 201):
            log.info("WhatsApp message sent to %s (sid=%s)", to, resp.json().get("sid"))
            return True
        else:
            log.error(
                "Twilio API error %s: %s", resp.status_code, resp.text[:500]
            )
            return False
    except Exception:
        log.exception("Failed to send WhatsApp message to %s", to)
        return False


# ---------------------------------------------------------------------------
# Inbound: validate Twilio webhook signature (HMAC-SHA1)
# ---------------------------------------------------------------------------

def validate_twilio_signature(
    url: str,
    params: dict[str, str],
    signature: str,
    auth_token: str,
) -> bool:
    """
    Validate Twilio's X-Twilio-Signature header.

    Algorithm (per https://www.twilio.com/docs/usage/security):
    1. Take the full URL of the request.
    2. Sort POST parameters alphabetically by key.
    3. Append each key-value pair to the URL (no delimiters).
    4. HMAC-SHA1 the result with your AuthToken.
    5. Base64-encode the HMAC.
    6. Compare with the provided signature.
    """
    if not signature or not auth_token:
        return False

    # Build the data string
    data = url
    for key in sorted(params.keys()):
        data += key + params[key]

    # Compute expected signature
    mac = hmac.new(
        auth_token.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha1,
    )
    expected = base64.b64encode(mac.digest()).decode("utf-8")

    return hmac.compare_digest(expected, signature)

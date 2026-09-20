"""Transactional email (OTP codes, notices) via Resend's HTTP API.

Resend is plain email infrastructure (like hosting), not a verification
provider: it only delivers the message. Pricing: free up to 3,000 emails per
month / 100 per day; Pro $20 per 50,000 (resend.com/pricing).

When RESEND_API_KEY is not configured, `send_email` returns False and callers
decide how to degrade (the OTP flow falls back to demo mode outside production).
"""

from __future__ import annotations

import logging

import httpx

from backend.app.config.settings import settings

logger = logging.getLogger(__name__)

_RESEND_URL = "https://api.resend.com/emails"


def email_configured() -> bool:
    return bool(settings.resend_api_key)


async def send_email(to: str, subject: str, text: str) -> bool:
    """Send a plain-text email. Returns True only if the provider accepted it."""
    if not email_configured():
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                _RESEND_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={"from": settings.email_from, "to": [to], "subject": subject, "text": text},
            )
        if resp.status_code >= 300:
            logger.warning("Email send rejected (%s): %s", resp.status_code, resp.text[:200])
            return False
        return True
    except httpx.HTTPError as exc:
        logger.warning("Email send failed: %s", exc)
        return False

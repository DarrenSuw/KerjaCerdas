"""Shareable job links + QR posters (`/j/<public_code>`).

The employer puts this link / QR where they already recruit (Instagram bio,
WhatsApp groups, a poster at the shop, a job fair). Applicants land on the
public job page and apply through KerjaCerdas instead of flooding WhatsApp
with PDFs. The QR is rendered server-side as SVG with `segno` (pure Python,
no external service).
"""

from __future__ import annotations

import io
import secrets

from backend.app.config.settings import settings

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I — easy to type from a poster
CODE_LENGTH = 7
DEFAULT_PUBLIC_URL = "https://kerjacerdas.tech"


def new_public_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(CODE_LENGTH))


def public_path(code: str) -> str:
    return f"/j/{code}"


def resolve_origin(requested: str | None) -> str:
    """Only encode origins we serve (CORS allow-list), so a QR can't point elsewhere."""
    allowed = {o.rstrip("/") for o in settings.cors_allow_origins}
    if requested and requested.rstrip("/") in allowed:
        return requested.rstrip("/")
    return DEFAULT_PUBLIC_URL


def qr_svg(url: str) -> bytes:
    import segno

    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="svg", scale=8, border=2, dark="#111111")
    return buf.getvalue()

"""Email verification (OTP) — the only identity check KerjaCerdas runs in-house.

No NIK / KTP / ijazah / NPWP is collected (UU PDP data minimisation). Skill
claims are verified with skill quizzes (routers/quiz.py) and HR confirmation;
the candidate's identity is checked by HR at the interview (KTP), as today.
Job postings are protected by AutoMod + admin review (services/trust/).
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from backend.app.api.dependencies import get_current_user
from backend.app.config.settings import settings
from backend.app.db.models import OTPRecord, User
from backend.app.db.postgres_store import set_user_email_verified
from backend.app.db.session import async_session
from backend.app.services.email.sender import email_configured, send_email
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

_OTP_TTL_SECONDS = 600  # 10 minutes
_OTP_MAX_ATTEMPTS = 5

router = APIRouter(prefix="/verify", tags=["verify"])


def _hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class EmailOtpVerifyReq(BaseModel):
    code: str = Field(min_length=6, max_length=6)


@router.get("/status")
async def verification_status(current_user: User = Depends(get_current_user)) -> dict:
    return {"email": current_user.email, "email_verified": bool(current_user.email_verified)}


@router.post("/email/send")
async def send_email_otp(current_user: User = Depends(get_current_user)) -> dict:
    """Send a 6-digit code to the account's own email address.

    With RESEND_API_KEY set the code is emailed. Without it, the code is only
    returned in the response while OTP demo mode is on (never in production
    by default) — otherwise the endpoint fails closed.
    """
    if current_user.email_verified:
        return {"status": "ALREADY_VERIFIED", "email": current_user.email}

    can_email = email_configured()
    if not can_email and not settings.otp_demo_enabled:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Pengiriman email belum dikonfigurasi. Hubungi admin KerjaCerdas.",
        )

    code = f"{secrets.randbelow(1_000_000):06d}"
    async with async_session() as session:
        await session.execute(delete(OTPRecord).where(OTPRecord.user_id == current_user.id))
        session.add(
            OTPRecord(
                user_id=current_user.id,
                destination=current_user.email,
                code_hash=_hash_token(code),
                expires_at=datetime.now(UTC) + timedelta(seconds=_OTP_TTL_SECONDS),
                attempts=0,
                verified=False,
            )
        )
        await session.commit()

    sent = False
    if can_email:
        sent = await send_email(
            current_user.email,
            "Kode verifikasi KerjaCerdas",
            f"Kode verifikasi email kamu: {code}\nBerlaku 10 menit. Jangan bagikan kode ini.",
        )
    if not sent and not settings.otp_demo_enabled:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Email gagal dikirim. Coba lagi.")

    body: dict = {
        "request_id": str(uuid.uuid4()),
        "status": "SENT",
        "email": current_user.email,
        "expires_in_seconds": _OTP_TTL_SECONDS,
        "mode": "email" if sent else "demo",
    }
    if not sent:
        body["demo_code"] = code
        body["message"] = f"[DEMO] Email belum dikonfigurasi. Kode: {code}"
    return body


@router.post("/email/verify")
async def verify_email_otp(
    req: EmailOtpVerifyReq, current_user: User = Depends(get_current_user)
) -> dict:
    submitted = _hash_token(req.code.strip())
    now = datetime.now(UTC)
    async with async_session() as session:
        stmt = (
            select(OTPRecord)
            .where(OTPRecord.user_id == current_user.id, OTPRecord.verified.is_(False))
            .order_by(OTPRecord.created_at.desc())
        )
        entry = (await session.execute(stmt)).scalars().first()
        if not entry:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Kode tidak ditemukan. Kirim ulang.")

        expires = entry.expires_at if entry.expires_at.tzinfo else entry.expires_at.replace(tzinfo=UTC)
        if now > expires:
            await session.delete(entry)
            await session.commit()
            raise HTTPException(status.HTTP_410_GONE, "Kode sudah kedaluwarsa. Kirim ulang.")

        entry.attempts += 1
        if entry.attempts > _OTP_MAX_ATTEMPTS:
            await session.delete(entry)
            await session.commit()
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Terlalu banyak percobaan.")

        if not secrets.compare_digest(submitted, entry.code_hash):
            remaining = _OTP_MAX_ATTEMPTS - entry.attempts
            await session.commit()
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"Kode salah. {remaining} percobaan tersisa."
            )
        entry.verified = True
        await session.commit()

    await set_user_email_verified(current_user.id)
    return {"status": "VERIFIED", "email": current_user.email, "email_verified": True}

"""Trust policy: employer badges, first-job review, strikes and the audit log.

Badges shown on every job (candidates judge for themselves):
  email_verified   the employer account proved its email via OTP
  company_email    ...and that email's domain matches the company website
                   (free mail like gmail.com never qualifies)
  admin_reviewed   an admin manually checked public proof links
                   (Google Maps listing, Instagram business, website)

Strike ladder (strikes expire 90 days after the last one):
  1 = warning, 2 = limited to one active job for 30 days, 3+ = suspended.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from backend.app.config.settings import settings
from backend.app.db import postgres_store as store
from backend.app.db.schemas import Employer, JobPosting, VerificationStatus
from backend.app.db.schemas_proof import ModerationEvent
from backend.app.services.trust.automod import Verdict

STRIKE_EXPIRY_DAYS = 90
LIMITED_DAYS = 30
_FREE_MAIL = {"gmail.com", "yahoo.com", "yahoo.co.id", "outlook.com", "hotmail.com", "icloud.com",
              "ymail.com", "proton.me", "protonmail.com", "live.com"}


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _domain(value: str | None) -> str:
    if not value:
        return ""
    host = urlparse(value if "//" in value else f"//{value}").hostname or ""
    return host.lower().removeprefix("www.")


def employer_badges(employer: Employer | None, user) -> dict:
    email = (getattr(user, "email", "") or "").lower()
    email_ok = bool(getattr(user, "email_verified", False))
    mail_domain = email.split("@")[-1] if "@" in email else ""
    site = _domain(getattr(employer, "website", None))
    company_email = bool(
        email_ok and mail_domain and mail_domain not in _FREE_MAIL
        and site and (mail_domain == site or mail_domain.endswith("." + site))
    )
    admin_reviewed = bool(employer and employer.verified == VerificationStatus.VERIFIED)
    return {"email_verified": email_ok, "company_email": company_email, "admin_reviewed": admin_reviewed}


def strike_state(employer: Employer, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    last = _aware(employer.last_strike_at)
    strikes = employer.strikes if last and now - last < timedelta(days=STRIKE_EXPIRY_DAYS) else 0
    limited = strikes == 2 and last is not None and now - last < timedelta(days=LIMITED_DAYS)
    return {"strikes": strikes, "limited": limited, "suspended": strikes >= 3}


async def add_strike(employer: Employer) -> dict:
    state = strike_state(employer)
    employer.strikes = state["strikes"] + 1
    employer.last_strike_at = datetime.now(UTC)
    await store.get_repositories().employers.upsert(employer)
    return strike_state(employer)


async def log_event(job: JobPosting, actor: str, action: str, reasons=None, note: str = "") -> None:
    await store.get_repositories().moderation_events.upsert(
        ModerationEvent(job_id=job.id, employer_id=job.employer_id, actor=actor,
                        action=action, reasons=reasons or [], note=note)
    )


def set_moderation(job: JobPosting, status: str, reasons: list[dict]) -> None:
    """Single place that keeps the invariant: only published jobs are active."""
    job.moderation_status = status
    job.moderation_reasons = reasons
    if status != "published":
        job.is_active = False


async def apply_verdict(job: JobPosting, employer: Employer, user, verdict: Verdict,
                        first_job: bool) -> dict:
    """Apply an AutoMod verdict (+ first-job review) to a job; returns the poster notice."""
    reasons = list(verdict.reasons)
    decision = verdict.decision
    badges = employer_badges(employer, user)
    trusted = badges["company_email"] or badges["admin_reviewed"]
    if decision == "published" and first_job and settings.moderation_first_job_review and not trusted:
        decision = "held"
        reasons.append({
            "rule": "first_job_review", "severity": "info", "excerpt": "",
            "fix": "Lowongan pertama ditinjau admin (biasanya < 24 jam). Verifikasi email "
                   "perusahaan atau ajukan 'Ditinjau admin' agar berikutnya langsung tayang.",
        })
    set_moderation(job, decision, reasons)
    if decision == "published":
        job.is_active = True
    strike = None
    if decision == "rejected":
        strike = await add_strike(employer)
    return {"moderation_status": decision, "reasons": reasons, "strike": strike}


def notice_text(notice: dict) -> str:
    status = notice["moderation_status"]
    if status == "published":
        return "Lowongan tayang."
    head = "Lowongan ditolak" if status == "rejected" else "Lowongan ditahan untuk ditinjau"
    lines = [f"{head}:"]
    for r in notice["reasons"]:
        lines.append(f"- {r['fix']}" + (f' (kalimat: "{r["excerpt"]}")' if r.get("excerpt") else ""))
    lines.append("Kamu bisa mengedit lalu mengirim ulang, atau mengajukan banding.")
    return "\n".join(lines)

"""Employer hiring tools (split out of employer.py to keep files small).

GET  /employer/applications/{id}/interview-kit   AI questions per candidate (Beacon/Lighthouse)
POST /employer/applications/{id}/confirm-skills   HR ticks "skill terbukti" after the interview
GET  /employer/jobs/{id}/applicants.csv            export (Beacon/Lighthouse)
POST /employer/jobs/{id}/appeal                    appeal a held/rejected posting
GET  /employer/trust                               badges, strikes, review status
POST /employer/trust/review-request                ask for the "Ditinjau admin" badge
"""

from __future__ import annotations

import csv
import io

from backend.app.api.dependencies import get_current_user, require_employer
from backend.app.db.models import User
from backend.app.db.postgres_store import (
    find_applications_by_job_id,
    find_employer_by_user_id,
    get_repositories,
)
from backend.app.db.schemas import ApplicationStatus, VerificationStatus
from backend.app.db.schemas_proof import SkillEvidence
from backend.app.services.billing.plans import entitlements_for
from backend.app.services.hiring.interview_kit import build_kit
from backend.app.services.matching.evidence import skill_key
from backend.app.services.matching.matcher import score_pair
from backend.app.services.trust import policy
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/employer", tags=["Employer hiring"],
                   dependencies=[Depends(require_employer)])

_AFTER_INTERVIEW = {ApplicationStatus.INTERVIEW, ApplicationStatus.OFFERED,
                    ApplicationStatus.HIRED, ApplicationStatus.REJECTED}


class SkillConfirmation(BaseModel):
    name: str = Field(max_length=120)
    confirmed: bool


class ConfirmSkillsReq(BaseModel):
    skills: list[SkillConfirmation] = Field(max_length=30)


class AppealReq(BaseModel):
    message: str = Field(min_length=10, max_length=2000)


class ReviewRequest(BaseModel):
    links: list[str] = Field(min_length=1, max_length=5)


async def _owned_application(app_id: str, user: User):
    repos = get_repositories()
    app = await repos.applications.get(app_id)
    employer = await find_employer_by_user_id(user.id)
    job = await repos.jobs.get(app.job_id) if app else None
    if not app or not employer or not job or job.employer_id != employer.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lamaran tidak ditemukan")
    return app, job, employer


async def _require_premium(user: User, job_id: str) -> None:
    ent = await entitlements_for(user.id)
    if not ent.premium_for_job(job_id):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Fitur ini tersedia di paket Beacon (per lowongan) atau Lighthouse.",
        )


@router.get("/applications/{app_id}/interview-kit")
async def interview_kit(app_id: str, current_user: User = Depends(get_current_user)):
    app, job, _ = await _owned_application(app_id, current_user)
    await _require_premium(current_user, job.id)
    seeker = await get_repositories().seekers.get(app.seeker_id)
    if not seeker:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil kandidat tidak ditemukan")
    return {"application_id": app.id, **await build_kit(job, seeker)}


@router.post("/applications/{app_id}/confirm-skills")
async def confirm_skills(app_id: str, req: ConfirmSkillsReq,
                         current_user: User = Depends(get_current_user)):
    """HR confirmation is the strongest proof (weight 1.0) — only after an interview."""
    app, job, employer = await _owned_application(app_id, current_user)
    if ApplicationStatus(app.status) not in _AFTER_INTERVIEW:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Konfirmasi skill hanya setelah kandidat diwawancarai.")
    repos = get_repositories()
    seeker = await repos.seekers.get(app.seeker_id)
    if not seeker:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil kandidat tidak ditemukan")

    allowed = {skill_key(s) for s in [*job.required_skills, *job.nice_to_have_skills]}
    allowed |= {skill_key(s.name) for s in seeker.skills}
    confirmed, rejected = [], []
    for item in req.skills:
        key = skill_key(item.name)
        if key not in allowed:
            continue
        await repos.skill_evidence.upsert(SkillEvidence(
            seeker_id=seeker.id, skill=key, source="hr", source_id=app.id,
            employer_id=employer.id, confirmed=item.confirmed))
        (confirmed if item.confirmed else rejected).append(item.name)
        if item.confirmed:
            match = next((s for s in seeker.skills if skill_key(s.name) == key), None)
            if match:
                match.proof_level, match.proof_date = "hr_confirmed", None
            else:
                from backend.app.db.schemas import Skill

                seeker.skills.append(Skill(name=item.name, proof_level="hr_confirmed"))
    await repos.seekers.upsert(seeker)
    return {"application_id": app.id, "confirmed": confirmed, "not_confirmed": rejected}


@router.get("/jobs/{job_id}/applicants.csv")
async def export_applicants(job_id: str, current_user: User = Depends(get_current_user)):
    repos = get_repositories()
    job = await repos.jobs.get(job_id)
    employer = await find_employer_by_user_id(current_user.id)
    if not job or not employer or job.employer_id != employer.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lowongan tidak ditemukan")
    await _require_premium(current_user, job.id)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["nama", "email", "skor", "band", "skill terbukti", "status", "sumber", "melamar"])
    rows = []
    for app in await find_applications_by_job_id(job.id):
        if app.status == ApplicationStatus.SAVED:
            continue
        seeker = await repos.seekers.get(app.seeker_id)
        user = await repos.users.get(seeker.user_id) if seeker else None
        live = score_pair(seeker, job) if seeker else {"score": 0, "band": "", "skill_proof": []}
        proven = [p["name"] for p in live["skill_proof"] if p["status"] in ("quiz", "hr_confirmed")]
        rows.append([seeker.full_name if seeker else "", user.email if user else "",
                     round(live["score"] * 100), live["band"], "; ".join(proven),
                     str(app.status.value if hasattr(app.status, "value") else app.status),
                     app.source, app.created_at.strftime("%Y-%m-%d")])
    for row in sorted(rows, key=lambda r: -r[2]):
        writer.writerow(row)
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="pelamar-{job.id[:8]}.csv"'})


@router.post("/jobs/{job_id}/appeal")
async def appeal(job_id: str, req: AppealReq, current_user: User = Depends(get_current_user)):
    repos = get_repositories()
    job = await repos.jobs.get(job_id)
    employer = await find_employer_by_user_id(current_user.id)
    if not job or not employer or job.employer_id != employer.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lowongan tidak ditemukan")
    if job.moderation_status == "published":
        raise HTTPException(status.HTTP_409_CONFLICT, "Lowongan ini sudah tayang.")
    await policy.log_event(job, "employer", "appealed", note=req.message.strip())
    if job.moderation_status == "rejected":
        policy.set_moderation(job, "held", job.moderation_reasons)
        await repos.jobs.upsert(job)
    return {"job_id": job.id, "moderation_status": job.moderation_status, "appeal": "received"}


@router.get("/trust")
async def trust_status(current_user: User = Depends(get_current_user)):
    employer = await find_employer_by_user_id(current_user.id)
    if not employer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil perusahaan belum dibuat")
    review = ("approved" if employer.verified == VerificationStatus.VERIFIED
              else "pending" if employer.verified == VerificationStatus.PENDING else "none")
    return {"badges": policy.employer_badges(employer, current_user),
            "strikes": policy.strike_state(employer),
            "review_status": review, "review_links": employer.review_links}


@router.post("/trust/review-request")
async def request_review(req: ReviewRequest, current_user: User = Depends(get_current_user)):
    employer = await find_employer_by_user_id(current_user.id)
    if not employer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil perusahaan belum dibuat")
    links = [ln.strip() for ln in req.links if ln.strip().startswith(("http://", "https://"))]
    if not links:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sertakan minimal satu tautan http(s).")
    employer.review_links = links[:5]
    if employer.verified != VerificationStatus.VERIFIED:
        employer.verified = VerificationStatus.PENDING
    await get_repositories().employers.upsert(employer)
    return {"review_status": "pending", "review_links": employer.review_links}

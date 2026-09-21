"""Public job-link surface: `/j/<code>` pages, QR posters, candidate reports.

GET  /public/jobs/{code}          job + company + trust badges (no login needed)
GET  /public/jobs/{code}/qr.svg   printable QR poster image for the link
POST /public/jobs/{code}/report   "Laporkan lowongan" (login required, 1 per user)

Enough distinct reports automatically hide the job for admin review.
"""

from __future__ import annotations

from backend.app.api.dependencies import get_current_user
from backend.app.api.routers.jobs import invalidate_jobs_cache
from backend.app.config.settings import settings
from backend.app.db.models import User
from backend.app.db.postgres_store import (
    find_job_by_public_code,
    find_reports_for_job,
    get_repositories,
)
from backend.app.db.schemas_proof import JobReport
from backend.app.services.hiring.links import public_path, qr_svg, resolve_origin
from backend.app.services.regions import get_region_name
from backend.app.services.trust import policy
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/public/jobs", tags=["public-jobs"])

REPORT_REASONS = {
    "minta_biaya": "Meminta biaya dari pelamar",
    "palsu": "Lowongan / perusahaan palsu",
    "diskriminatif": "Syarat diskriminatif",
    "kontak_mencurigakan": "Kontak mencurigakan",
    "lainnya": "Lainnya",
}


class ReportReq(BaseModel):
    reason: str = Field(max_length=40)
    detail: str = Field(default="", max_length=1000)


async def _job_or_404(code: str):
    job = await find_job_by_public_code(code.strip().upper())
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lowongan tidak ditemukan")
    return job


@router.get("/{code}")
async def public_job(code: str):
    job = await _job_or_404(code)
    if not job.is_active or job.moderation_status != "published":
        return {"withdrawn": True, "detail": "Lowongan ini sudah tidak aktif atau sedang ditinjau moderasi."}

    repos = get_repositories()
    employer = await repos.employers.get(job.employer_id)
    owner = await repos.users.get(employer.user_id) if employer else None
    data = job.model_dump(
        exclude={"embedding", "embedding_model", "client_ref", "moderation_reasons"}
    )
    data.update({
        "company_name": employer.company_name if employer else "",
        "industry": employer.industry if employer else "",
        "website": employer.website if employer else None,
        "location": get_region_name(job.region_code),
        "badges": policy.employer_badges(employer, owner),
        "accepting_applications": job.is_active,
        "share_path": public_path(job.public_code),
        "report_reasons": REPORT_REASONS,
    })
    return data


@router.get("/{code}/qr.svg")
async def public_job_qr(code: str, origin: str | None = Query(default=None, max_length=200)):
    job = await _job_or_404(code)
    if not job.is_active or job.moderation_status != "published":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lowongan tidak aktif")
    url = resolve_origin(origin) + public_path(job.public_code)
    return Response(content=qr_svg(url), media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=86400"})


@router.post("/{code}/report", status_code=status.HTTP_201_CREATED)
async def report_job(code: str, req: ReportReq, current_user: User = Depends(get_current_user)):
    if req.reason not in REPORT_REASONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Alasan laporan tidak dikenal")
    job = await _job_or_404(code)
    repos = get_repositories()
    try:
        await repos.job_reports.upsert(
            JobReport(job_id=job.id, reporter_user_id=current_user.id,
                      reason=req.reason, detail=req.detail.strip())
        )
    except IntegrityError:
        return {"status": "already_reported"}

    open_reports = [r for r in await find_reports_for_job(job.id) if not r.resolved]
    hidden = False
    if len(open_reports) >= settings.moderation_report_threshold and job.moderation_status == "published":
        reasons = [{"rule": "reports", "severity": "soft", "excerpt": "",
                    "fix": f"{len(open_reports)} laporan pengguna — admin akan meninjau."}]
        policy.set_moderation(job, "held", reasons)
        await repos.jobs.upsert(job)
        invalidate_jobs_cache()
        await policy.log_event(job, "reports", "held", reasons)
        hidden = True
    return {"status": "reported", "job_hidden_for_review": hidden}

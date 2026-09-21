"""Public job-link surface: `/j/<code>` pages, QR posters, candidate reports.

GET  /public/jobs/{code}          job + company + trust badges (no login needed)
GET  /public/jobs/{code}/qr.svg   printable QR poster image for the link
POST /public/jobs/{code}/report   "Laporkan lowongan" (login required, 1 per user)

Enough distinct reports automatically hide the job for admin review.
"""

from __future__ import annotations

from datetime import UTC, datetime

from backend.app.api.dependencies import get_current_user
from backend.app.api.routers.jobs import invalidate_jobs_cache
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
    # Which published rule (R1..R6) the reporter says was broken. The AI
    # reviewer is only ever asked about the rule cited here, which is what
    # keeps it from free-associating its way to removing a real posting.
    rule_cited: str = Field(default="", max_length=40)
    detail: str = Field(default="", max_length=1000)


async def _job_or_404(code: str):
    job = await find_job_by_public_code(code.strip().upper())
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lowongan tidak ditemukan")
    return job


@router.get("/{code}")
async def public_job(code: str):
    job = await _job_or_404(code)
    if not policy.is_publicly_visible(job):
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
    if not policy.is_publicly_visible(job):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lowongan tidak aktif")
    url = resolve_origin(origin) + public_path(job.public_code)
    return Response(content=qr_svg(url), media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=86400"})


@router.post("/{code}/report", status_code=status.HTTP_201_CREATED)
async def report_job(code: str, req: ReportReq, current_user: User = Depends(get_current_user)):
    """Community report. Reaching the threshold FLAGS a posting; it never hides it.

    The old behaviour hid a posting the moment three distinct users reported it,
    with no check that anything had been broken — so three coordinated accounts
    could remove a competitor, while a single obvious scam stayed live until a
    third person happened to complain. Now:

      report -> weighted by how much the reporter has at stake
             -> threshold reached -> "flagged", STILL VISIBLE, with a notice
             -> AI checks the posting against the cited rule only
                  violation  -> held (hidden), employer notified, appeal open
                  clear/ragu -> stays up, queued for a human

    Nothing here hides a posting on accusation alone.
    """
    from backend.app.services.trust import rules as rulebook_mod
    from backend.app.services.trust.automod import review_reported_posting

    if req.reason not in REPORT_REASONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Alasan laporan tidak dikenal")
    if req.rule_cited and req.rule_cited not in rulebook_mod.RULES_BY_ID:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Aturan yang dikutip tidak dikenal")

    job = await _job_or_404(code)
    repos = get_repositories()
    try:
        await repos.job_reports.upsert(
            JobReport(job_id=job.id, reporter_user_id=current_user.id,
                      reason=req.reason, rule_cited=req.rule_cited,
                      detail=req.detail.strip())
        )
    except IntegrityError:
        return {"status": "already_reported"}

    open_reports = [r for r in await find_reports_for_job(job.id) if not r.resolved]
    weighted = await _weighted_report_score(open_reports, job.id)

    result = {
        "status": "reported",
        "job_hidden_for_review": False,
        "under_review": job.moderation_status == "flagged",
    }
    if job.moderation_status != "published":
        return result
    if rulebook_mod.flag_state(weighted, len(open_reports)) != "flagged":
        return result

    cited = [r.rule_cited for r in open_reports if r.rule_cited]
    reasons = [{
        "rule": "community_flag", "severity": "soft", "excerpt": "",
        "fix": f"{len(open_reports)} laporan pengguna sedang diperiksa.",
    }]
    policy.set_moderation(job, "flagged", reasons)
    await repos.jobs.upsert(job)
    invalidate_jobs_cache()
    await policy.log_event(job, "reports", "flagged", reasons)
    result["under_review"] = True

    review = await review_reported_posting(job.title, job.description or "", cited)
    if review["verdict"] == "violation":
        rule = rulebook_mod.RULES_BY_ID.get(review["rule"])
        held_reasons = [{
            "rule": review["rule"] or "community_flag", "severity": "soft",
            "excerpt": review["note"],
            "fix": rule.fix if rule else "Perbaiki lalu ajukan tinjauan ulang.",
        }]
        policy.set_moderation(job, "held", held_reasons)
        await repos.jobs.upsert(job)
        invalidate_jobs_cache()
        await policy.log_event(job, "report_review", "held", held_reasons, note=review["note"])
        result["job_hidden_for_review"] = True
    else:
        # Clear or uncertain: the posting stays up and a human decides. An
        # uncertain model must never be the thing that removes a live advert.
        await policy.log_event(job, "report_review", "needs_admin", [], note=review["note"])
    return result


async def _weighted_report_score(reports, job_id: str) -> int:
    """Sum reporter weights. A count of accounts is not a measure of harm."""
    from backend.app.services.trust.rules import reporter_weight

    repos = get_repositories()
    total = 0
    applicants: set[str] = set()
    try:
        applicants = {
            a.seeker_id for a in await repos.applications.list() if a.job_id == job_id
        }
    except Exception:  # noqa: BLE001 — weighting must never break reporting
        applicants = set()

    for rep in reports:
        user = await repos.users.get(rep.reporter_user_id)
        if user is None:
            continue
        history = [
            r for r in await repos.job_reports.list()
            if r.reporter_user_id == rep.reporter_user_id and r.upheld is not None
        ]
        created = rep.created_at
        age_days = 0.0
        if getattr(user, "created_at", None) is not None:
            created_at = user.created_at
            created_at = created_at if created_at.tzinfo else created_at.replace(tzinfo=UTC)
            age_days = (datetime.now(UTC) - created_at).total_seconds() / 86400
        total += reporter_weight(
            email_verified=bool(getattr(user, "email_verified", False)),
            applied_to_job=user.id in applicants or rep.reporter_user_id in applicants,
            account_age_days=age_days,
            upheld_reports=sum(1 for r in history if r.upheld),
            dismissed_reports=sum(1 for r in history if r.upheld is False),
        )
        _ = created
    return total


@router.get("/rules")
async def posting_rules():
    """The same rulebook shown to employers, reporters and the AI reviewer."""
    from backend.app.services.trust.rules import rulebook

    return {"rules": rulebook()}

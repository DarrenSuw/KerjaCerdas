"""Where one application stands among the others for the same job.

This is the Prism benefit, and it is deliberately the cheapest thing we sell:
every number below is read from rows written when the candidate applied, so a
lookup costs **Rp0** — no embedding call, no LLM call, no re-scoring. That
matters twice. It keeps the seeker tier's margin from depending on usage, and it
means the feature cannot drift from what the employer sees, because both read
the same stored `match_score`.

What Prism buys is **visibility of your own position**, never movement in it.
The free tier already shows the band and which skills are missing; Prism adds
the exact place in the queue and the per-component arithmetic behind it. Paying
changes nothing about the ordering, and nothing here is writable — this module
has no side effects at all.
"""

from __future__ import annotations

from backend.app.db.postgres_store import find_applications_by_job_id
from backend.app.db.schemas import Application, ApplicationStatus


# Ties share a rank ("joint 4th"), which is why this is not a list index. Two
# candidates with identical stored scores are genuinely level, and showing one
# of them as strictly ahead would be an ordering we cannot justify.
def _rank_of(score: float, scores: list[float]) -> int:
    return sum(1 for s in scores if s > score) + 1


async def rank_for_application(app: Application) -> dict:
    """Exact standing for one application, plus the arithmetic behind it.

    `total` counts everyone who actually applied to the job, including this
    candidate, and matches the field the employer sees. Withdrawn applications
    stay in the denominator on purpose — the candidate placed in the field that
    applied, and quietly shrinking it would flatter the number — but bookmarks
    are not applications and are excluded.
    """
    # SAVED rows are bookmarks from people who never applied. The employer's
    # own applicant list excludes them (employer.py), so counting them here
    # would show the candidate a standing that disagrees with the queue HR
    # actually reads — and would pad the field with people who are not
    # competing at all.
    siblings = [
        a for a in await find_applications_by_job_id(app.job_id)
        if a.status != ApplicationStatus.SAVED
    ]
    scores = [a.match_score for a in siblings]
    rank = _rank_of(app.match_score, scores)
    total = len(scores) or 1

    # Percentile is reported only when the field is large enough for it to mean
    # anything. "Top 50%" out of two applicants is noise dressed as insight.
    percentile = None
    if total >= 10:
        percentile = round(100 * (total - rank + 1) / total)

    # The key is `proof_level` — `evidence.skill_snapshot` writes
    # {name, proof_level}. Reading `level` matched nothing, so both lists were
    # always empty and every candidate was told all their skills were proven,
    # which is the opposite of the advice they needed.
    proven = [s for s in app.skill_snapshot if s.get("proof_level") in ("quiz", "hr_confirmed")]
    claimed = [s for s in app.skill_snapshot if s.get("proof_level") == "claimed"]

    return {
        "application_id": app.id,
        "job_id": app.job_id,
        "rank": rank,
        "total_applicants": total,
        "percentile": percentile,
        "score": round(app.match_score, 3),
        # The per-skill evidence stored at apply time — the honest answer to
        # "why am I not higher?", and the one that points at a quiz rather than
        # at more keywords.
        "skills": app.skill_snapshot,
        "proven_count": len(proven),
        "claimed_count": len(claimed),
        # Said plainly, because it is the whole product promise: the way up this
        # list is proof, and it is free.
        "how_to_improve": (
            f"{len(claimed)} skill masih berupa klaim. Lulus kuisnya menaikkan bobot "
            "tiap skill dari 0,30 ke 0,85 — dan kuis gratis di semua paket."
            if claimed
            else "Semua skill yang diminta lowongan ini sudah terbukti."
        ),
    }

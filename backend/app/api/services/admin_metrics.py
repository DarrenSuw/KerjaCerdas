"""Numbers the business model depends on, computed from real rows.

- ai_cost: Rupiah per AI action (ai_logs tokens x Gemini price table x USD/IDR)
- funnel: applications by source (board / job link), quiz completion + pass rate
- outcomes: interview rate per score band (does the match score predict interviews?)
- plans: active orders and pending payments
- moderation: held / rejected jobs, open reports
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from backend.app.config.settings import settings
from backend.app.db.postgres_store import get_repositories

_REACHED_INTERVIEW = {"interview", "offered", "hired"}


def _band(score: float) -> str:
    if score >= settings.band_strong_threshold:
        return "strong"
    return "possible" if score >= settings.band_possible_threshold else "stretch"


def _cost_idr(model: str, tin: int, tout: int) -> float:
    prices = settings.ai_prices_usd_per_million
    p_in, p_out = prices.get(model) or prices.get(settings.gemini_chat_model) or (0.30, 2.50)
    return (tin * p_in + tout * p_out) / 1_000_000 * settings.usd_to_idr


async def collect_metrics() -> dict:
    repos = get_repositories()
    now = datetime.now(UTC)

    by_task: dict[str, dict] = defaultdict(lambda: {"calls": 0, "tokens_in": 0, "tokens_out": 0,
                                                     "cost_idr": 0.0, "failures": 0})
    for log in await repos.ai_logs.list():
        t = by_task[log.task]
        t["calls"] += 1
        t["tokens_in"] += log.tokens_in
        t["tokens_out"] += log.tokens_out
        t["failures"] += 0 if log.success else 1
        t["cost_idr"] += _cost_idr(log.model, log.tokens_in, log.tokens_out)
    ai_cost = {k: {**v, "cost_idr": round(v["cost_idr"], 2),
                   "avg_cost_idr_per_call": round(v["cost_idr"] / v["calls"], 2) if v["calls"] else 0}
               for k, v in by_task.items()}

    apps = [a for a in await repos.applications.list() if a.status != "saved"]
    reached = {e.application_id for e in await repos.status_events.list()
               if e.to_status in _REACHED_INTERVIEW}
    bands: dict[str, dict] = defaultdict(lambda: {"applications": 0, "reached_interview": 0})
    sources: dict[str, int] = defaultdict(int)
    for a in apps:
        b = bands[_band(a.match_score or 0.0)]
        b["applications"] += 1
        b["reached_interview"] += 1 if a.id in reached or a.status in _REACHED_INTERVIEW else 0
        sources[a.source] += 1
    for b in bands.values():
        b["interview_rate"] = round(b["reached_interview"] / b["applications"], 3) if b["applications"] else 0

    attempts = [q for q in await repos.quiz_attempts.list() if q.submitted_at]
    per_skill: dict[str, dict] = defaultdict(lambda: {"attempts": 0, "passed": 0})
    for q in attempts:
        per_skill[q.skill]["attempts"] += 1
        per_skill[q.skill]["passed"] += 1 if q.passed else 0

    orders = await repos.plan_orders.list()
    live = [o for o in orders if o.status == "active" and o.expires_at
            and (o.expires_at if o.expires_at.tzinfo else o.expires_at.replace(tzinfo=UTC)) > now]
    last30 = [o for o in live if o.starts_at and
              (o.starts_at if o.starts_at.tzinfo else o.starts_at.replace(tzinfo=UTC)) > now - timedelta(days=30)]
    jobs = await repos.jobs.list()
    reports = await repos.job_reports.list()

    return {
        "generated_at": now.isoformat(),
        "usd_to_idr": settings.usd_to_idr,
        "ai_cost_by_task": ai_cost,
        "applications": {"total": len(apps), "by_source": dict(sources)},
        "outcomes_by_band": dict(bands),
        "quizzes": {"submitted": len(attempts), "passed": sum(1 for q in attempts if q.passed),
                    "by_skill": dict(per_skill)},
        "plans": {
            "active_by_plan": {p: sum(1 for o in live if o.plan == p) for p in ("beacon", "lighthouse", "prism")},
            "revenue_last_30_days_idr": sum(o.amount_idr for o in last30),
            "pending_orders": sum(1 for o in orders if o.status == "pending"),
        },
        "moderation": {
            "published": sum(1 for j in jobs if j.moderation_status == "published"),
            "held": sum(1 for j in jobs if j.moderation_status == "held"),
            "rejected": sum(1 for j in jobs if j.moderation_status == "rejected"),
            "open_reports": sum(1 for r in reports if not r.resolved),
        },
    }

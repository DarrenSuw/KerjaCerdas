"""Plan catalogue and entitlement checks (Spark / Beacon / Lighthouse / Prism).

Employers
  Spark       Rp0          1 active job, ALL applicants ranked, core features
  Beacon      Rp49.000     per job for 30 days: AI interview questions, CSV
                           export, pipeline tools, reverse matching
  Lighthouse  Rp149.000    per 30 days: up to 5 active jobs, all Beacon features
Job seekers
  Free        Rp0          matching, skill gap, unlimited quizzes (retake next
                           day), advisor 10 messages / day
  Prism       Rp15.000     per 30 days: exact application rank + score
                           breakdown, advisor 30 messages / day

The paywall sits on what COSTS us money and saves an employer time (interview
kits, export, sourcing), not on how many applicants may be seen. Ranking is a
free computation; charging for it punished candidates rather than us, and left
the free tier able to do the whole job for a one-person hire anyway.

Prism no longer shortens the quiz retake cooldown. That was money buying a
faster route to a proof badge, which moves a match score — the one thing the
product promises paying can never do.

Payment is manual for now (QRIS / bank transfer): a plan order stays
"pending" until an admin confirms the payment and activates it for 30 days.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from backend.app.config.settings import settings
from backend.app.db import postgres_store as store
from backend.app.db.schemas_proof import PlanOrder

PLAN_DAYS = 30
LIGHTHOUSE_ACTIVE_JOBS = 5
SPARK_ACTIVE_JOBS = 1

# Advisor metering. Both tiers are now measured in the SAME unit (per day), and
# the paid one is strictly larger. It used to be 10/day free versus 100/30 days
# on Prism — i.e. 300 a month free against 100 a month paid, with the paid user
# locked out for up to 30 days instead of until tomorrow. Paying bought less.
# Any future change must keep PRISM > FREE on the same axis.
ADVISOR_FREE_PER_DAY = 10
ADVISOR_PRISM_PER_DAY = 30

# Reverse matching (searching candidates who have NOT applied) is the employer
# feature that is genuinely worth money: it is sourcing, not screening. Ranked
# APPLICANTS are deliberately uncapped on every tier, including free — ranking
# costs Rp0 to compute, so capping it saved us nothing and cost a candidate
# ranked 21st their only chance of being seen.
TALENT_SEARCHES_SPARK = 0
TALENT_SEARCHES_BEACON = 30
TALENT_SEARCHES_LIGHTHOUSE = 150

EMPLOYER_PLANS = ("beacon", "lighthouse")
SEEKER_PLANS = ("prism",)


def plan_price(plan: str) -> int:
    return {
        "beacon": settings.plan_price_beacon,
        "lighthouse": settings.plan_price_lighthouse,
        "prism": settings.plan_price_prism,
    }[plan]


def catalogue() -> dict:
    return {
        "employer": [
            {"plan": "spark", "price_idr": 0, "period": "gratis",
             "features": ["1 lowongan aktif", "Link + QR lowongan",
                          "Semua pelamar diperingkat — tanpa batas",
                          "Badge skill terbukti", "Centang 'skill terbukti' setelah wawancara"]},
            {"plan": "beacon", "price_idr": settings.plan_price_beacon,
             "period": "per lowongan / 30 hari",
             "features": ["Semua fitur Spark", "Pertanyaan wawancara AI per kandidat",
                          "Ekspor pelamar (CSV)",
                          f"Cari kandidat yang belum melamar ({TALENT_SEARCHES_BEACON}x / 30 hari)"]},
            {"plan": "lighthouse", "price_idr": settings.plan_price_lighthouse,
             "period": "per 30 hari",
             "features": ["Semua fitur Beacon", f"Hingga {LIGHTHOUSE_ACTIVE_JOBS} lowongan aktif",
                          f"Cari kandidat ({TALENT_SEARCHES_LIGHTHOUSE}x / 30 hari)"]},
        ],
        "seeker": [
            {"plan": "free", "price_idr": 0, "period": "gratis",
             "features": ["Skor kecocokan + skill gap + rekomendasi kursus",
                          "Kuis skill tanpa batas (ulang besoknya)",
                          "Band skor + skill yang kurang untuk tiap lamaran",
                          f"Advisor {ADVISOR_FREE_PER_DAY} pesan / hari"]},
            {"plan": "prism", "price_idr": settings.plan_price_prism, "period": "per 30 hari",
             "features": ["Peringkat persis tiap lamaran (mis. #14 dari 62)",
                          "Rincian skor per komponen",
                          f"Advisor {ADVISOR_PRISM_PER_DAY} pesan / hari"]},
        ],
        "note": ("Membayar tidak pernah mengubah skor kecocokan maupun peringkat. "
             "Kuis, skor, dan urutan pelamar sama untuk semua paket."),
        "payment_instructions": settings.payment_instructions,
    }


def _is_live(order: PlanOrder, now: datetime) -> bool:
    if order.status != "active" or order.expires_at is None:
        return False
    exp = order.expires_at if order.expires_at.tzinfo else order.expires_at.replace(tzinfo=UTC)
    return exp > now


@dataclass
class Entitlements:
    lighthouse_until: datetime | None = None
    beacon_jobs: set[str] = field(default_factory=set)
    prism_until: datetime | None = None

    @property
    def has_lighthouse(self) -> bool:
        return self.lighthouse_until is not None

    @property
    def has_prism(self) -> bool:
        return self.prism_until is not None

    def job_tier(self, job_id: str) -> str:
        if self.has_lighthouse:
            return "lighthouse"
        return "beacon" if job_id in self.beacon_jobs else "spark"

    def premium_for_job(self, job_id: str) -> bool:
        if not settings.plan_limits_enforced:
            return True
        return self.job_tier(job_id) != "spark"


async def entitlements_for(user_id: str) -> Entitlements:
    now = datetime.now(UTC)
    ent = Entitlements()
    for o in await store.find_orders_by_user(user_id):
        if not _is_live(o, now):
            continue
        if o.plan == "lighthouse":
            ent.lighthouse_until = max(filter(None, [ent.lighthouse_until, o.expires_at]))
        elif o.plan == "beacon" and o.job_id:
            ent.beacon_jobs.add(o.job_id)
        elif o.plan == "prism":
            ent.prism_until = max(filter(None, [ent.prism_until, o.expires_at]))
    return ent


def talent_search_limit(ent: Entitlements) -> int:
    """Reverse-matching searches allowed per 30 days.

    Quota goes HERE and not on ranked applicants. Scoring people who applied is
    free to compute and capping it only hides candidates; searching people who
    did not apply is sourcing, which is the thing an employer will actually pay
    for and the thing we want a deliberate, countable limit on.
    """
    if ent.has_lighthouse:
        return TALENT_SEARCHES_LIGHTHOUSE
    return TALENT_SEARCHES_BEACON if ent.beacon_jobs else TALENT_SEARCHES_SPARK


def active_job_limit(ent: Entitlements) -> int:
    """Active jobs allowed that are NOT individually covered by a Beacon order."""
    return LIGHTHOUSE_ACTIVE_JOBS if ent.has_lighthouse else SPARK_ACTIVE_JOBS


async def activate(order: PlanOrder, admin_email: str) -> PlanOrder:
    now = datetime.now(UTC)
    order.status = "active"
    order.activated_by = admin_email
    order.starts_at = now
    order.expires_at = now + timedelta(days=PLAN_DAYS)
    order.updated_at = now
    await store.get_repositories().plan_orders.upsert(order)
    return order

"""Plan catalogue and entitlement checks (Spark / Beacon / Lighthouse / Prism).

Employers
  Spark       Rp0          1 active job, first 20 applicants ranked, core features
  Beacon      Rp29.000     per job for 30 days: unlimited ranked applicants,
                           AI interview questions, applicant export
  Lighthouse  Rp99.000     per 30 days: up to 5 active jobs, all Beacon features
Job seekers
  Free        Rp0          matching, skill gap, quizzes (retake after 7 days),
                           advisor 10 messages / day
  Prism       Rp25.000     per 30 days: quiz retake after 2 days, advisor 100
                           messages / 30 days. Paying never changes a match score.

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
ADVISOR_FREE_PER_DAY = 10
ADVISOR_PRISM_PER_30_DAYS = 100

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
                          f"Peringkat AI untuk {settings.spark_ranked_applicant_limit} pelamar pertama",
                          "Badge skill terbukti", "Centang 'skill terbukti' setelah wawancara"]},
            {"plan": "beacon", "price_idr": settings.plan_price_beacon, "period": "per lowongan / 30 hari",
             "features": ["Semua fitur Spark", "Pelamar tanpa batas diperingkat",
                          "Pertanyaan wawancara AI per kandidat", "Ekspor pelamar (CSV)"]},
            {"plan": "lighthouse", "price_idr": settings.plan_price_lighthouse, "period": "per 30 hari",
             "features": ["Semua fitur Beacon", f"Hingga {LIGHTHOUSE_ACTIVE_JOBS} lowongan aktif"]},
        ],
        "seeker": [
            {"plan": "free", "price_idr": 0, "period": "gratis",
             "features": ["Skor kecocokan + skill gap + rekomendasi kursus", "Kuis skill (ulang setelah 7 hari)",
                          f"Advisor {ADVISOR_FREE_PER_DAY} pesan / hari"]},
            {"plan": "prism", "price_idr": settings.plan_price_prism, "period": "per 30 hari",
             "features": ["Ulang kuis setelah 2 hari", f"Advisor {ADVISOR_PRISM_PER_30_DAYS} pesan / 30 hari"]},
        ],
        "note": "Membayar tidak pernah menaikkan skor kecocokan atau peringkat.",
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

"""Pydantic projections of the v2 proof-of-skill tables (db/models_proof.py).

Same contract as db/schemas.py: every field here has a same-named ORM column,
enforced by tests/unit/test_schema_parity.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.app.db.schemas import TimestampedModel, _now, _uid


class SkillQuestion(TimestampedModel):
    id: str = Field(default_factory=_uid)
    skill: str
    skill_label: str = ""
    question: str
    options: list[str]
    correct_index: int
    reviewed: bool = False
    active: bool = True


class QuizAttempt(TimestampedModel):
    id: str = Field(default_factory=_uid)
    seeker_id: str
    skill: str
    question_ids: list[str]
    deadline_at: datetime
    submitted_at: datetime | None = None
    answers: list[int] = []
    score: int = 0
    passed: bool = False


class SkillEvidence(TimestampedModel):
    id: str = Field(default_factory=_uid)
    seeker_id: str
    skill: str
    source: Literal["quiz", "hr"]
    source_id: str = ""
    employer_id: str | None = None
    confirmed: bool = True


class JobReport(TimestampedModel):
    id: str = Field(default_factory=_uid)
    job_id: str
    reporter_user_id: str
    reason: str
    detail: str = ""
    resolved: bool = False


class ModerationEvent(BaseModel):
    id: str = Field(default_factory=_uid)
    job_id: str
    employer_id: str
    actor: str
    action: str
    reasons: list[dict] = []
    note: str = ""
    created_at: datetime = Field(default_factory=_now)


PlanName = Literal["beacon", "lighthouse", "prism"]


class PlanOrder(TimestampedModel):
    id: str = Field(default_factory=_uid)
    user_id: str
    plan: PlanName
    job_id: str | None = None
    amount_idr: int
    status: Literal["pending", "active", "cancelled"] = "pending"
    payment_reference: str = ""
    activated_by: str = ""
    starts_at: datetime | None = None
    expires_at: datetime | None = None


class ApplicationStatusEvent(BaseModel):
    id: str = Field(default_factory=_uid)
    application_id: str
    job_id: str
    from_status: str
    to_status: str
    match_score: float = 0.0
    created_at: datetime = Field(default_factory=_now)

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
    # "human" (starter bank / admin-approved) | "ai_auto" (generated, passed the
    # mechanical validator) | "ai_draft" (generated, failed it — never served).
    # Provenance is kept per row so the admin queue and any claim we make about
    # the bank stay honest; "reviewed" alone cannot tell the three apart.
    source: str = "human"
    review_note: str = ""


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
    # See models_proof.QuizAttempt.proof_eligible.
    proof_eligible: bool = True


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
    # Which published rule the reporter says was broken. The AI reviewer checks
    # the posting against THIS rule only, so a report that cites nothing cannot
    # trigger an automated verdict.
    rule_cited: str = ""
    detail: str = ""
    resolved: bool = False
    # Set when an admin or the AI reviewer finds no violation. Upheld/dismissed
    # history is what makes a reporter's weight mean anything.
    upheld: bool | None = None


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
    # Required by the API when to_status == "rejected": the seeker's whole
    # complaint is "tidak dapat kabar, tidak tahu apa yang kurang", and this is
    # the field that answers it. Also the only structured outcome data we will
    # ever have for testing whether a high score really predicts an interview.
    reason_code: str = ""
    reason_note: str = ""
    created_at: datetime = Field(default_factory=_now)

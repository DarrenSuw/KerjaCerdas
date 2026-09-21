"""ORM tables for the v2 "proven skills" features.

Split out of models.py (already large) to keep files small. Registered on the
same `Base` metadata — models.py imports this module at the bottom so every
`from backend.app.db.models import Base` sees these tables too.

Tables:
  skill_questions          — reviewed multiple-choice question bank, one skill per row group
  quiz_attempts            — one timed quiz attempt (5 random questions) by a seeker
  skill_evidence           — every proof event: quiz pass, HR confirm / not-confirm
  job_reports              — candidate "Laporkan lowongan" reports
  moderation_events        — AutoMod / admin audit log for job postings
  plan_orders              — plan purchases (manual payment, activated by an admin)
  application_status_events — history of application status changes (outcome data)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.models import Base, TimestampedMixin, _now, _uid


class SkillQuestion(Base, TimestampedMixin):
    __tablename__ = "skill_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    # Canonical skill key (lower-case, see services/matching/evidence.skill_key).
    skill: Mapped[str] = mapped_column(String(80), index=True)
    skill_label: Mapped[str] = mapped_column(String(120), default="")
    question: Mapped[str] = mapped_column(Text)
    options: Mapped[list[Any]] = mapped_column(JSON, default=list)
    correct_index: Mapped[int] = mapped_column(Integer)
    # False until a human (HR practitioner / teacher) has reviewed the item.
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # human | ai_auto | ai_draft — see schemas_proof.SkillQuestion.
    source: Mapped[str] = mapped_column(String(20), default="human")
    review_note: Mapped[str] = mapped_column(Text, default="")


class QuizAttempt(Base, TimestampedMixin):
    __tablename__ = "quiz_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    seeker_id: Mapped[str] = mapped_column(String(36), index=True)
    skill: Mapped[str] = mapped_column(String(80), index=True)
    question_ids: Mapped[list[Any]] = mapped_column(JSON, default=list)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    answers: Mapped[list[Any]] = mapped_column(JSON, default=list)
    score: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    # False when the bank was too thin to draw without repeating the previous
    # attempt. Such an attempt is still playable and still scored — it just
    # cannot award a badge, because passing questions you were shown days ago
    # is not evidence of the skill. See services/quiz/service._pick_questions.
    proof_eligible: Mapped[bool] = mapped_column(Boolean, default=True)


class SkillEvidence(Base, TimestampedMixin):
    __tablename__ = "skill_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    seeker_id: Mapped[str] = mapped_column(String(36), index=True)
    skill: Mapped[str] = mapped_column(String(80), index=True)
    source: Mapped[str] = mapped_column(String(20))  # "quiz" | "hr"
    source_id: Mapped[str] = mapped_column(String(36), default="")  # attempt / application id
    employer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=True)


class JobReport(Base, TimestampedMixin):
    __tablename__ = "job_reports"
    __table_args__ = (UniqueConstraint("job_id", "reporter_user_id", name="uq_job_report_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    job_id: Mapped[str] = mapped_column(String(36), index=True)
    reporter_user_id: Mapped[str] = mapped_column(String(36))
    reason: Mapped[str] = mapped_column(String(40))
    rule_cited: Mapped[str] = mapped_column(String(40), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    upheld: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class ModerationEvent(Base):
    __tablename__ = "moderation_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    job_id: Mapped[str] = mapped_column(String(36), index=True)
    employer_id: Mapped[str] = mapped_column(String(36), index=True)
    actor: Mapped[str] = mapped_column(String(80))  # "automod" | "reports" | admin email | "employer"
    action: Mapped[str] = mapped_column(String(30))  # published | held | rejected | appealed | strike
    reasons: Mapped[list[Any]] = mapped_column(JSON, default=list)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class PlanOrder(Base, TimestampedMixin):
    __tablename__ = "plan_orders"
    __table_args__ = (Index("ix_plan_orders_user_status", "user_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    plan: Mapped[str] = mapped_column(String(20))  # beacon | lighthouse | prism
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # Beacon only
    amount_idr: Mapped[int] = mapped_column(Integer)
    # pending (waiting for payment check) | active | cancelled
    status: Mapped[str] = mapped_column(String(20), default="pending")
    payment_reference: Mapped[str] = mapped_column(String(120), default="")
    activated_by: Mapped[str] = mapped_column(String(255), default="")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApplicationStatusEvent(Base):
    __tablename__ = "application_status_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    application_id: Mapped[str] = mapped_column(String(36), index=True)
    job_id: Mapped[str] = mapped_column(String(36), index=True)
    from_status: Mapped[str] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    match_score: Mapped[float] = mapped_column(default=0.0)
    reason_code: Mapped[str] = mapped_column(String(40), default="")
    reason_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

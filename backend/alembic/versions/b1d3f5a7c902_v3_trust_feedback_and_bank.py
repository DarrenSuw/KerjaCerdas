"""v3: question provenance, weighted reports, and mandatory rejection reasons.

Revision ID: b1d3f5a7c902
Revises: a2b4c6d8e0f1

Three additions, each backing a behaviour change in this release:

skill_questions.source / review_note
    The bank now tops itself up toward 30 questions per skill so that a retake
    never repeats what the candidate just saw. Generated items that pass the
    mechanical validator are served immediately, which makes "reviewed" too
    coarse to be honest on its own: it can no longer distinguish a question a
    practitioner approved from one a regex approved. `source` keeps that
    distinction ("human" | "ai_auto" | "ai_draft") so nothing we say about the
    bank is a claim the data cannot support.

job_reports.rule_cited / upheld
    Reports now name the published rule they allege was broken, which is the
    only question the AI reviewer is ever asked, and `upheld` records how the
    accusation ended so a reporter's weight can reflect their track record.

quiz_attempts.proof_eligible
    A quiz drawn from a bank too thin to avoid repeating the previous attempt
    is still playable, but must not award a badge: passing questions you were
    shown yesterday is not evidence of the skill, and the badge carries a 0.85
    proof weight. The flag is per attempt rather than per skill because the
    bank refills, so the very next attempt can be clean.

application_status_events.reason_code / reason_note
    A rejection now requires a reason. This is the data that answers the
    candidate's "tidak tahu apa yang kurang", and the only structured outcome
    we will have for testing whether a high match score predicts an interview.

All columns are nullable or defaulted, so the upgrade is safe on populated
tables and the downgrade is a clean drop.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b1d3f5a7c902"
down_revision: str | Sequence[str] | None = "a2b4c6d8e0f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_ADDED: tuple[tuple[str, str, sa.types.TypeEngine, str | None], ...] = (
    ("skill_questions", "source", sa.String(length=20), "'human'"),
    ("skill_questions", "review_note", sa.Text(), "''"),
    ("job_reports", "rule_cited", sa.String(length=40), "''"),
    ("job_reports", "upheld", sa.Boolean(), None),
    ("quiz_attempts", "proof_eligible", sa.Boolean(), "true"),
    ("application_status_events", "reason_code", sa.String(length=40), "''"),
    ("application_status_events", "reason_note", sa.Text(), "''"),
)


def _existing_columns(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    for table, column, type_, default in _ADDED:
        present = _existing_columns(table)
        # A table missing entirely means this deployment has not run the v2
        # revision's table creation yet through create_all; skip rather than
        # fail, the same defensive stance a2b4c6d8e0f1 takes.
        if not present or column in present:
            continue
        op.add_column(
            table,
            sa.Column(column, type_, nullable=True, server_default=sa.text(default) if default else None),
        )


def downgrade() -> None:
    for table, column, _type, _default in reversed(_ADDED):
        present = _existing_columns(table)
        if column in present:
            op.drop_column(table, column)

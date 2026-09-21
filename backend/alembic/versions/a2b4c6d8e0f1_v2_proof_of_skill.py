"""v2 proof-of-skill release: quizzes, trust/moderation, plans, outcome data.

Adds
  users.email_verified                       email OTP result
  employers.review_links/strikes/last_strike_at   "Ditinjau admin" + strike ladder
  jobs.public_code/moderation_status/moderation_reasons   share link + AutoMod
  applications.skill_snapshot/source                      outcome data
  tables: skill_questions, quiz_attempts, skill_evidence, job_reports,
          moderation_events, plan_orders, application_status_events,
          otps + query_embeddings (never created by any earlier migration —
          they only ever existed via the app's startup create_all())
Renames
  otps.phone -> otps.destination (now an email address, VARCHAR(255))
Drops (UU PDP data minimisation — identity documents are no longer collected)
  seekers.nik, seekers.nik_verified, seekers.ijazah_verified, employers.npwp

Replay-safe: app startup's create_all() may already have created the new
tables, so every step checks what exists first.

Revision ID: a2b4c6d8e0f1
Revises: f7a1c5e9b432
Create Date: 2026-09-19
"""

import secrets
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a2b4c6d8e0f1"
down_revision: Union[str, Sequence[str], None] = "f7a1c5e9b432"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

_NEW_COLUMNS = {
    "users": [sa.Column("email_verified", sa.Boolean(), server_default=sa.false(), nullable=False)],
    "employers": [
        sa.Column("review_links", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("strikes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_strike_at", sa.DateTime(timezone=True), nullable=True),
    ],
    "jobs": [
        sa.Column("public_code", sa.String(16), nullable=True),
        sa.Column("moderation_status", sa.String(20), server_default="published", nullable=False),
        sa.Column("moderation_reasons", sa.JSON(), server_default="[]", nullable=False),
    ],
    "applications": [
        sa.Column("skill_snapshot", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("source", sa.String(20), server_default="board", nullable=False),
    ],
}

_DROPPED = {"seekers": ["nik", "nik_verified", "ijazah_verified"], "employers": ["npwp"]}

# Tables this revision CREATES but did not INTRODUCE. Both predate v2 — the
# pre-v2 app used them, they were just never written into a migration, so this
# revision backfills them. A downgrade must therefore leave them in place: the
# revision it rolls back to still needs `otps` to verify a code and
# `query_embeddings` for its cache, and dropping them would destroy live OTP
# records and the persistent embedding cache rather than restore a prior state.
_BACKFILLED_TABLES = ("otps", "query_embeddings")


def _ts():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    ]


def _new_tables() -> dict:
    return {
        "skill_questions": [
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("skill", sa.String(80), index=True),
            sa.Column("skill_label", sa.String(120), server_default=""),
            sa.Column("question", sa.Text()),
            sa.Column("options", sa.JSON()),
            sa.Column("correct_index", sa.Integer()),
            sa.Column("reviewed", sa.Boolean(), server_default=sa.false()),
            sa.Column("active", sa.Boolean(), server_default=sa.true()),
            *_ts(),
        ],
        "quiz_attempts": [
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("seeker_id", sa.String(36), index=True),
            sa.Column("skill", sa.String(80), index=True),
            sa.Column("question_ids", sa.JSON()),
            sa.Column("deadline_at", sa.DateTime(timezone=True)),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("answers", sa.JSON()),
            sa.Column("score", sa.Integer(), server_default="0"),
            sa.Column("passed", sa.Boolean(), server_default=sa.false()),
            *_ts(),
        ],
        "skill_evidence": [
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("seeker_id", sa.String(36), index=True),
            sa.Column("skill", sa.String(80), index=True),
            sa.Column("source", sa.String(20)),
            sa.Column("source_id", sa.String(36), server_default=""),
            sa.Column("employer_id", sa.String(36), nullable=True),
            sa.Column("confirmed", sa.Boolean(), server_default=sa.true()),
            *_ts(),
        ],
        "job_reports": [
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("job_id", sa.String(36), index=True),
            sa.Column("reporter_user_id", sa.String(36)),
            sa.Column("reason", sa.String(40)),
            sa.Column("detail", sa.Text(), server_default=""),
            sa.Column("resolved", sa.Boolean(), server_default=sa.false()),
            *_ts(),
            sa.UniqueConstraint("job_id", "reporter_user_id", name="uq_job_report_user"),
        ],
        "moderation_events": [
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("job_id", sa.String(36), index=True),
            sa.Column("employer_id", sa.String(36), index=True),
            sa.Column("actor", sa.String(80)),
            sa.Column("action", sa.String(30)),
            sa.Column("reasons", sa.JSON()),
            sa.Column("note", sa.Text(), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), index=True),
        ],
        "plan_orders": [
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), index=True),
            sa.Column("plan", sa.String(20)),
            sa.Column("job_id", sa.String(36), nullable=True),
            sa.Column("amount_idr", sa.Integer()),
            sa.Column("status", sa.String(20), server_default="pending"),
            sa.Column("payment_reference", sa.String(120), server_default=""),
            sa.Column("activated_by", sa.String(255), server_default=""),
            sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            *_ts(),
        ],
        # Neither of the next two tables was created by ANY migration — they
        # existed only because the app's startup create_all() made them. On a
        # database built purely from migrations (CI, and any real deployment
        # that migrates before first boot) they were simply absent: email OTP
        # verification had nowhere to write, and the persistent query-embedding
        # cache silently degraded to a miss on every lookup. Created here with
        # the post-v2 column names, so the rename below is a no-op for them.
        "otps": [
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), index=True, nullable=False),
            sa.Column("destination", sa.String(255), index=True, nullable=False),
            sa.Column("code_hash", sa.String(64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), index=True, nullable=False),
            sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
            sa.Column("verified", sa.Boolean(), server_default=sa.false(), nullable=False),
            *_ts(),
        ],
        "query_embeddings": [
            sa.Column("cache_key", sa.String(64), primary_key=True),
            sa.Column("model", sa.String(100), nullable=False),
            sa.Column("embedding", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.text("now()"), index=True),
        ],
        "application_status_events": [
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("application_id", sa.String(36), index=True),
            sa.Column("job_id", sa.String(36), index=True),
            sa.Column("from_status", sa.String(20)),
            sa.Column("to_status", sa.String(20)),
            sa.Column("match_score", sa.Float(), server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), index=True),
        ],
    }


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    for table, columns in _NEW_COLUMNS.items():
        if not insp.has_table(table):
            continue
        existing = {c["name"] for c in insp.get_columns(table)}
        for col in columns:
            if col.name not in existing:
                op.add_column(table, col)

    for table, cols in _new_tables().items():
        if not insp.has_table(table):
            op.create_table(table, *cols)
    if "ix_plan_orders_user_status" not in {i["name"] for i in sa.inspect(bind).get_indexes("plan_orders")}:
        op.create_index("ix_plan_orders_user_status", "plan_orders", ["user_id", "status"])

    otp_insp = sa.inspect(bind)  # fresh: otps may have been created just above
    otp_cols = {c["name"] for c in otp_insp.get_columns("otps")} if otp_insp.has_table("otps") else set()
    if "phone" in otp_cols and "destination" not in otp_cols:
        op.alter_column("otps", "phone", new_column_name="destination",
                        type_=sa.String(255), existing_type=sa.String(30))

    # Backfill share codes for existing jobs, then enforce uniqueness.
    rows = bind.execute(sa.text("SELECT id FROM jobs WHERE public_code IS NULL")).fetchall()
    used: set[str] = set()
    for (job_id,) in rows:
        code = "".join(secrets.choice(_ALPHABET) for _ in range(7))
        while code in used:
            code = "".join(secrets.choice(_ALPHABET) for _ in range(7))
        used.add(code)
        bind.execute(sa.text("UPDATE jobs SET public_code = :c WHERE id = :i"), {"c": code, "i": job_id})
    if "ix_jobs_public_code" not in {i["name"] for i in sa.inspect(bind).get_indexes("jobs")}:
        op.create_index("ix_jobs_public_code", "jobs", ["public_code"], unique=True)

    for table, cols in _DROPPED.items():
        if not sa.inspect(bind).has_table(table):
            continue
        existing = {c["name"] for c in sa.inspect(bind).get_columns(table)}
        for col in cols:
            if col in existing:
                op.drop_column(table, col)


def downgrade() -> None:
    op.add_column("seekers", sa.Column("nik", sa.String(64), nullable=True))
    op.add_column("seekers", sa.Column("nik_verified", sa.String(20), server_default="unverified"))
    op.add_column("seekers", sa.Column("ijazah_verified", sa.String(20), server_default="unverified"))
    op.add_column("employers", sa.Column("npwp", sa.String(50), nullable=True))
    op.drop_index("ix_jobs_public_code", table_name="jobs")
    op.alter_column("otps", "destination", new_column_name="phone",
                    type_=sa.String(30), existing_type=sa.String(255))
    op.drop_index("ix_plan_orders_user_status", table_name="plan_orders")
    for table in reversed(list(_new_tables())):
        if table in _BACKFILLED_TABLES:
            continue  # predates this revision — see _BACKFILLED_TABLES
        op.drop_table(table)
    for table, columns in _NEW_COLUMNS.items():
        for col in columns:
            op.drop_column(table, col.name)

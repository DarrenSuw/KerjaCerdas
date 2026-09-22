"""
KerjaCerdas — Database Engine
==============================
Async SQLAlchemy engine and session factory for PostgreSQL.
Supports fallback to SQLite for demo/development mode.

Production target: PostgreSQL 15 with the pgvector extension.
"""

from __future__ import annotations

import logging

from sqlalchemy import event, inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.app.config.settings import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


# ---------------------------------------------------------------------------
# Engine factory — production uses asyncpg, dev/demo uses aiosqlite
# ---------------------------------------------------------------------------


def _build_engine(database_url: str):
    """
    Build the async SQLAlchemy engine from a database URL.

    Supports:
      - postgresql+asyncpg://...  (production)
      - sqlite+aiosqlite:///...   (demo / local development)
    """
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # asyncpg doesn't accept sslmode as a URL query param — strip it
    if "postgresql+asyncpg" in database_url and "sslmode" in database_url:
        import urllib.parse

        parsed = urllib.parse.urlparse(database_url)
        qs = {k: v for k, v in urllib.parse.parse_qsl(parsed.query) if k != "sslmode"}
        database_url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(qs)))

    # SQLite needs special handling for async + foreign keys
    is_sqlite = "sqlite" in database_url
    is_neon = "neon.tech" in database_url

    if is_neon:
        # Rewrite to Neon's PgBouncer pooler endpoint, which stays alive even
        # when the serverless compute is suspended.  The pooler hostname is the
        # same as the direct hostname but with "-pooler" inserted before the
        # first ".".  e.g. ep-foo-bar.c-3.region.aws.neon.tech
        #                -> ep-foo-bar-pooler.c-3.region.aws.neon.tech
        import urllib.parse as _up

        _parsed = _up.urlparse(database_url)
        _host = _parsed.hostname or ""
        if _host and "-pooler" not in _host:
            _pooler_host = _host.replace(".", "-pooler.", 1)
            _netloc = _pooler_host
            if _parsed.port:
                _netloc = f"{_pooler_host}:{_parsed.port}"
            if _parsed.username:
                _userinfo = _parsed.username
                if _parsed.password:
                    _userinfo = f"{_parsed.username}:{_parsed.password}"
                _netloc = f"{_userinfo}@{_netloc}"
            database_url = _up.urlunparse(_parsed._replace(netloc=_netloc))
            logger.info("Neon: rewritten to pooler endpoint → %s", _host.split(".")[0] + "-pooler")

        # PgBouncer / Neon pooler requires prepared-statement caching disabled.
        connect_args: dict = {
            "statement_cache_size": 0,
            "command_timeout": 30,
            "timeout": 15,  # seconds to wait for Neon compute to wake up
        }
    elif is_sqlite:
        connect_args = {"check_same_thread": False}
    else:
        connect_args = {}

    if is_sqlite:
        engine = create_async_engine(
            database_url,
            echo=False,
            future=True,
            connect_args=connect_args,
        )

        @event.listens_for(engine.sync_engine, "connect")
        def _enable_fk(dbapi_conn, _):
            """Enable foreign key support for SQLite."""
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        engine = create_async_engine(
            database_url,
            echo=False,
            future=True,
            connect_args=connect_args,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
        )

    return engine


# ---------------------------------------------------------------------------
# Default engine + session (created lazily on first import / startup)
# ---------------------------------------------------------------------------

# Build from settings (reads .env) so the engine is correct even before the
# startup lifespan calls reconfigure() — and so standalone scripts that import
# this module pick up the same database (e.g. SQLite in dev).
engine = _build_engine(settings.effective_database_url)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def reconfigure(database_url: str) -> None:
    """
    Reconfigure the engine at runtime (called during app startup).

    Args:
        database_url: Full database connection string.
    """
    global engine, async_session_factory
    engine = _build_engine(database_url)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    logger.info(
        f"Database engine reconfigured → {database_url.split('@')[-1] if '@' in database_url else database_url}"
    )


async def get_session():
    """FastAPI dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


def _get_table_columns(sync_conn, table_name: str) -> set[str]:
    """Return the set of column names for a table if it exists."""
    inspector = inspect(sync_conn)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


async def _migrate_verification_logs_schema(conn) -> None:
    """Rename the legacy verification column to the generic hash name."""
    column_names = await conn.run_sync(_get_table_columns, "verification_logs")
    if "zk_commitment" in column_names and "verification_hash" not in column_names:
        await conn.execute(
            text("ALTER TABLE verification_logs RENAME COLUMN zk_commitment TO verification_hash")
        )
        logger.info("Migrated verification_logs.zk_commitment to verification_hash")


async def _migrate_applications_schema(conn) -> None:
    """Add note column to applications if missing (SQLite & local dev migration)."""
    column_names = await conn.run_sync(_get_table_columns, "applications")
    if column_names and "note" not in column_names:
        await conn.execute(text("ALTER TABLE applications ADD COLUMN note TEXT DEFAULT ''"))
        logger.info("Migrated applications: added note column")


# Columns added by the v2 proof-of-skill release (Alembic revision
# a2b4c6d8e0f1). create_all() only creates missing TABLES, so an existing
# local SQLite dev database also needs the new COLUMNS added in place.
# (table, column, complete static DDL) — literal SQL only, never built from
# strings at runtime.
_V2_COLUMNS: list[tuple[str, str, str]] = [
    ("users", "email_verified", "ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT 0"),
    ("employers", "review_links", "ALTER TABLE employers ADD COLUMN review_links JSON DEFAULT '[]'"),
    ("employers", "strikes", "ALTER TABLE employers ADD COLUMN strikes INTEGER DEFAULT 0"),
    ("employers", "last_strike_at", "ALTER TABLE employers ADD COLUMN last_strike_at TIMESTAMP"),
    ("jobs", "public_code", "ALTER TABLE jobs ADD COLUMN public_code VARCHAR(16)"),
    (
        "jobs",
        "moderation_status",
        "ALTER TABLE jobs ADD COLUMN moderation_status VARCHAR(20) DEFAULT 'published'",
    ),
    ("jobs", "moderation_reasons", "ALTER TABLE jobs ADD COLUMN moderation_reasons JSON DEFAULT '[]'"),
    (
        "applications",
        "skill_snapshot",
        "ALTER TABLE applications ADD COLUMN skill_snapshot JSON DEFAULT '[]'",
    ),
    ("applications", "source", "ALTER TABLE applications ADD COLUMN source VARCHAR(20) DEFAULT 'board'"),
]


# Columns added by the v3 trust/quiz release (Alembic revision b1d3f5a7c902).
# Same reason as _V2_COLUMNS: create_all() adds missing TABLES but never missing
# COLUMNS, so an existing local SQLite database keeps its old shape and then
# fails on the first query touching one of these. Adding the ORM columns without
# extending this list is exactly how a developer's working database breaks on
# `git pull`.
_V3_COLUMNS: list[tuple[str, str, str]] = [
    (
        "skill_questions",
        "source",
        "ALTER TABLE skill_questions ADD COLUMN source VARCHAR(20) DEFAULT 'human'",
    ),
    ("skill_questions", "review_note", "ALTER TABLE skill_questions ADD COLUMN review_note TEXT DEFAULT ''"),
    ("job_reports", "rule_cited", "ALTER TABLE job_reports ADD COLUMN rule_cited VARCHAR(40) DEFAULT ''"),
    ("job_reports", "upheld", "ALTER TABLE job_reports ADD COLUMN upheld BOOLEAN"),
    (
        "quiz_attempts",
        "proof_eligible",
        "ALTER TABLE quiz_attempts ADD COLUMN proof_eligible BOOLEAN DEFAULT 1",
    ),
    (
        "quiz_attempts",
        "status",
        "ALTER TABLE quiz_attempts ADD COLUMN status VARCHAR(20) DEFAULT 'in_progress'",
    ),
    (
        "application_status_events",
        "reason_code",
        "ALTER TABLE application_status_events ADD COLUMN reason_code VARCHAR(40) DEFAULT ''",
    ),
    (
        "application_status_events",
        "reason_note",
        "ALTER TABLE application_status_events ADD COLUMN reason_note TEXT DEFAULT ''",
    ),
]


async def _migrate_v2_columns(conn) -> None:
    cache: dict[str, set[str]] = {}
    for table, column, ddl in (*_V2_COLUMNS, *_V3_COLUMNS):
        if table not in cache:
            cache[table] = await conn.run_sync(_get_table_columns, table)
        if cache[table] and column not in cache[table]:
            await conn.execute(text(ddl))
            logger.info("Migrated %s: added %s", table, column)
    otp_cols = await conn.run_sync(_get_table_columns, "otps")
    if "phone" in otp_cols and "destination" not in otp_cols:
        await conn.execute(text("ALTER TABLE otps RENAME COLUMN phone TO destination"))


async def _assert_schema_current(conn) -> None:
    """Fail startup loudly when a PostgreSQL database is missing v2 columns.

    `create_all()` only creates missing TABLES — it can never ADD a column to a
    table that already exists. So an existing PostgreSQL deployment that hasn't
    had `alembic upgrade head` run against it starts up "successfully" and then
    500s on the first query touching users.email_verified, jobs.public_code or
    applications.skill_snapshot.

    Refusing to boot turns that into one clear message at deploy time instead of
    scattered runtime errors. The Docker image runs the upgrade in its
    entrypoint (backend/docker-entrypoint.sh); this is the backstop for
    deployments that start uvicorn some other way.
    """
    missing: list[str] = []
    cache: dict[str, set[str]] = {}
    for table, column, _ddl in _V2_COLUMNS:
        if table not in cache:
            cache[table] = await conn.run_sync(_get_table_columns, table)
        # An absent table is fine — create_all() just made it, with every column.
        if cache[table] and column not in cache[table]:
            missing.append(f"{table}.{column}")
    otp_cols = await conn.run_sync(_get_table_columns, "otps")
    if otp_cols and "destination" not in otp_cols:
        missing.append("otps.destination")

    if missing:
        raise RuntimeError(
            "Database schema is out of date — missing: "
            + ", ".join(missing)
            + ". Run `alembic upgrade head` (from the backend/ directory, with "
            "DATABASE_URL set) before starting the API."
        )


async def init_db() -> None:
    """Create all tables. Called once during application startup."""
    # Import models here so their metadata is registered before create_all.
    # db/models.py defines its own Base; use that one (it owns the ORM tables).
    from backend.app.db.models import Base as ModelsBase  # noqa: PLC0415

    is_sqlite = str(engine.url).startswith("sqlite")
    async with engine.begin() as conn:
        # pgvector: activate the extension before create_all attempts to
        # define VECTOR columns. Mirrors what the Alembic initial migration
        # already does (see alembic/versions/5a748883f1d9_initial_schema.py).
        # Skipped for SQLite (unit tests / demo mode) which has no extensions.
        if not is_sqlite:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(ModelsBase.metadata.create_all)
        await _migrate_verification_logs_schema(conn)
        await _migrate_applications_schema(conn)
        if is_sqlite:
            # SQLite is dev/test only and has no Alembic history of its own, so
            # the v2 columns are added in place here.
            await _migrate_v2_columns(conn)
        else:
            # PostgreSQL migrates through Alembic (CLAUDE.md: "Migrations via
            # Alembic only"). Verify rather than silently continue.
            await _assert_schema_current(conn)
    logger.info("[DB] Database tables created / verified successfully")

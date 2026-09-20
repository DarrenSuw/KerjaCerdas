"""Guards for the three deployment hazards found in PR #28 review.

1. A PostgreSQL database that never had `alembic upgrade head` run against it
   must fail startup loudly, not serve traffic and 500 on the first v2 column.
2. Changing GEMINI_EMBED_MODEL must not silently zero the cosine term — the
   re-embed path has to exist and be reachable.
3. Quota metering must work on SQLite (dev/test), where pg_advisory_xact_lock
   does not exist.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.app.api import database as db_module
from backend.app.db.postgres_store import consume_quota


class TestSchemaGuard:
    """`create_all()` cannot ADD a column to an existing table."""

    @pytest.mark.asyncio
    async def test_missing_v2_column_raises_with_the_fix_command(
        self, client, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A table that exists but lacks a v2 column must stop the boot.

        The introspection is stubbed rather than really dropping the column:
        SQLite refuses to DROP a column an index depends on, and the behaviour
        under test is the guard's reaction to a legacy schema, not SQLite DDL.
        """
        real = db_module._get_table_columns

        def legacy_jobs(sync_conn, table_name: str) -> set[str]:
            cols = real(sync_conn, table_name)
            return cols - {"public_code"} if table_name == "jobs" else cols

        monkeypatch.setattr(db_module, "_get_table_columns", legacy_jobs)
        async with db_module.engine.begin() as conn:
            with pytest.raises(RuntimeError) as err:
                await db_module._assert_schema_current(conn)
        assert "jobs.public_code" in str(err.value)
        assert "alembic upgrade head" in str(err.value)

    @pytest.mark.asyncio
    async def test_current_schema_passes(self, client) -> None:
        async with db_module.engine.begin() as conn:
            await db_module._assert_schema_current(conn)  # must not raise

    def test_every_v2_column_is_checked(self) -> None:
        """The guard reads _V2_COLUMNS, so a new column added there is covered."""
        checked = {f"{t}.{c}" for t, c, _ in db_module._V2_COLUMNS}
        for expected in ("users.email_verified", "jobs.public_code",
                         "applications.skill_snapshot", "applications.source"):
            assert expected in checked


class TestEmbeddingModelMigration:
    """Cross-model vectors score 0 on cosine — the entire cosine term."""

    def test_stale_model_tag_costs_the_whole_cosine_term(self) -> None:
        """Confirms the behaviour that makes re-embedding mandatory."""
        from backend.app.config.settings import settings
        from backend.app.db.schemas import JobPosting, SeekerProfile
        from backend.app.services.matching.matcher import score_pair

        vec = [0.1] * settings.gemini_embed_dim
        current = settings.gemini_embed_model

        def pair(job_model: str) -> float:
            job = JobPosting(employer_id="e1", title="Admin", description="Admin kantor",
                             region_code="3171", embedding=vec, embedding_model=job_model)
            seeker = SeekerProfile(user_id="u1", full_name="Dewi", region_code="3171",
                                   embedding=vec, embedding_model=current)
            return score_pair(seeker, job)["score"]

        # Identical vectors either way. Only the model tag differs.
        fresh = pair(current)
        stale = pair("gemini-embedding-001")
        # The whole cosine weight simply disappears — silently, no error anywhere.
        from backend.app.services.matching.matcher import _W_COSINE

        assert fresh - stale == pytest.approx(_W_COSINE, abs=0.01)

    def test_reembed_script_targets_the_configured_model(self) -> None:
        """The documented remedy must import and point at the current model."""
        import scripts.reembed as reembed

        from backend.app.config.settings import settings

        assert reembed.main is not None
        assert "scripts.reembed" in reembed.__doc__

        # .env.example must not drift from the code default again. Compared
        # against the FIELD default, not settings.gemini_embed_model — the live
        # value is whatever the developer's own .env says, which is exactly the
        # drift this test exists to catch.
        default_model = type(settings).model_fields["gemini_embed_model"].default
        env_example = db_module.__file__.rsplit("backend", 1)[0] + ".env.example"
        with open(env_example, encoding="utf-8") as fh:
            body = fh.read()
        assert f"GEMINI_EMBED_MODEL={default_model}" in body
        # And it must tell the reader that changing it requires a re-embed.
        assert "scripts.reembed" in body


class TestQuotaOnSqlite:
    """pg_advisory_xact_lock does not exist on SQLite."""

    @pytest.mark.asyncio
    async def test_consume_quota_meters_instead_of_erroring(self, seeker_account: dict) -> None:
        user_id = seeker_account["user"]["id"]
        since = datetime.now(UTC) - timedelta(days=1)
        assert await consume_quota(user_id, "test_quota", limit=2, since=since) is True
        assert await consume_quota(user_id, "test_quota", limit=2, since=since) is True
        # Third call is over the limit — refused, not a 500.
        assert await consume_quota(user_id, "test_quota", limit=2, since=since) is False


class TestPackagedDependencies:
    """A lazily imported module still has to be a declared dependency.

    `segno` is imported inside qr_svg(), so nothing fails until a request hits
    /public/jobs/{code}/qr.svg — which is how it passed locally (already in the
    dev environment) and 500'd in CI.
    """

    def test_lazily_imported_packages_are_declared(self) -> None:
        import tomllib
        from pathlib import Path

        pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
        with pyproject.open("rb") as fh:
            declared = tomllib.load(fh)["project"]["dependencies"]
        names = {d.split(">")[0].split("[")[0].split("=")[0].strip().lower() for d in declared}
        assert "segno" in names

    def test_qr_rendering_actually_works(self) -> None:
        from backend.app.services.hiring.links import qr_svg

        svg = qr_svg("https://kerjacerdas.tech/j/ABC2345")
        assert svg.startswith(b"<?xml") or b"<svg" in svg


class TestCsvInjection:
    """Applicant-controlled text lands in a file HR opens in a spreadsheet."""

    def test_formula_prefixes_are_neutralised(self) -> None:
        from backend.app.api.routers.hiring import _csv_safe

        for payload in ("=HYPERLINK(\"http://evil\",\"click\")", "+1+1", "-2+3", "@SUM(A1)"):
            assert _csv_safe(payload).startswith("'"), payload
        # Ordinary values must pass through untouched, including None.
        assert _csv_safe("Dewi Kartika") == "Dewi Kartika"
        assert _csv_safe(None) == ""
        assert _csv_safe("") == ""


class TestStatusEventOrdering:
    """A fabricated interview/hire event corrupts the metric we argue from."""

    def test_event_is_written_after_the_application(self) -> None:
        """Ordering is the whole fix, so assert it in the source, not by mocking
        two independent repository transactions."""
        from pathlib import Path

        src = (Path(__file__).resolve().parents[2] / "app/api/routers/employer.py").read_text(
            encoding="utf-8"
        )
        body = src[src.index("    pending_event: ApplicationStatusEvent | None = None"):]
        app_write = body.index("await repos.applications.upsert(app)")
        event_write = body.index("await repos.status_events.upsert(pending_event)")
        assert app_write < event_write, "history event must not be written before the status"


class TestMigrationsCoverEveryTable:
    """Every ORM table must be created by some migration.

    `otps` and `query_embeddings` were defined in models.py but created by no
    revision — they existed only because the app's startup create_all() made
    them. A database built purely from migrations (CI, and any deployment that
    migrates before first boot) therefore had no table to write email OTPs to,
    and the v2 revision crashed with NoSuchTableError inspecting `otps`.
    """

    def test_no_orm_table_is_missing_from_the_migrations(self) -> None:
        import re
        from pathlib import Path

        from backend.app.db import models_proof  # noqa: F401 — registers v2 tables
        from backend.app.db.models import Base

        created: set[str] = set()
        for path in (Path(__file__).resolve().parents[2] / "alembic/versions").glob("*.py"):
            src = path.read_text(encoding="utf-8")
            created |= set(re.findall(r'op\.create_table\(\s*[\'"]([a-z_]+)[\'"]', src))
            created |= set(re.findall(r"CREATE TABLE IF NOT EXISTS ([a-z_]+)", src))
            # The v2 revision builds its tables from a {name: columns} mapping.
            if "def _new_tables" in src:
                block = src[src.index("def _new_tables"):src.index("def upgrade")]
                created |= set(re.findall(r'^\s{8}"([a-z_]+)":', block, re.M))

        missing = sorted(set(Base.metadata.tables) - created)
        assert not missing, (
            f"ORM tables created by no migration: {missing}. A migration-built "
            "database will not have them — create_all() at startup is not a "
            "migration path (see CLAUDE.md)."
        )


def _v2_revision():
    """Import the v2 revision module so its table definitions can be inspected."""
    import importlib.util
    from pathlib import Path

    path = (Path(__file__).resolve().parents[2]
            / "alembic/versions/a2b4c6d8e0f1_v2_proof_of_skill.py")
    spec = importlib.util.spec_from_file_location("v2_revision", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestMigrationMatchesOrm:
    """A migration-built table must have the constraints the ORM declares."""

    def test_foreign_keys_match_the_orm(self) -> None:
        from backend.app.db import models_proof  # noqa: F401 — registers v2 tables
        from backend.app.db.models import Base

        for name, columns in _v2_revision()._new_tables().items():
            migrated = {
                (c.name, list(c.foreign_keys)[0]._colspec)
                for c in columns
                if getattr(c, "foreign_keys", None)
            }
            orm = {
                (c.name, list(c.foreign_keys)[0].target_fullname)
                for c in Base.metadata.tables[name].columns
                if c.foreign_keys
            }
            assert migrated == orm, (
                f"{name}: migration declares {migrated or 'no FKs'} but the ORM "
                f"declares {orm or 'no FKs'} — an Alembic-built database would "
                "lose referential integrity the model assumes."
            )


class TestDowngradePreservesPreExistingTables:
    """Rolling back must restore a prior state, not destroy live data."""

    def test_backfilled_tables_are_not_dropped(self) -> None:
        module = _v2_revision()
        # These predate the revision: it only backfills them into the migration
        # history, so a downgrade leaves them for the revision it rolls back to.
        assert set(module._BACKFILLED_TABLES) == {"otps", "query_embeddings"}
        for table in module._BACKFILLED_TABLES:
            assert table in module._new_tables(), f"{table} must still be created on upgrade"

    def test_every_other_new_table_is_still_dropped(self) -> None:
        module = _v2_revision()
        introduced = set(module._new_tables()) - set(module._BACKFILLED_TABLES)
        assert introduced == {
            "skill_questions", "quiz_attempts", "skill_evidence", "job_reports",
            "moderation_events", "plan_orders", "application_status_events",
        }

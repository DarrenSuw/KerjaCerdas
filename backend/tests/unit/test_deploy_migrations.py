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
    """Cross-model vectors score 0 on cosine — 45% of the match score."""

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
        # 0.45 of the score simply disappears — silently, with no error anywhere.
        assert fresh - stale == pytest.approx(0.45, abs=0.01)

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

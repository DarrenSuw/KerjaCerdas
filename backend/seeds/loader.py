"""Quiz bank seed loader — inserts JSON seed files into the DB on startup.

Called once during application startup, after `init_db()`. For each skill whose
bank is still empty in the database it bulk-inserts all questions from the
corresponding JSON seed file. Skills that already have questions are skipped so
this is safely idempotent.

Fast by design: one COUNT query per skill + a bulk INSERT; ~163 skills with
~30 questions each finishes in well under 2 seconds on a local Docker Postgres.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.app.db.models_proof import SkillQuestion
from backend.app.db.session import async_session

logger = logging.getLogger(__name__)

# Resolve the directory relative to this file so the loader works regardless
# of cwd (inside Docker the cwd is /app).
_DEFAULT_BANKS_DIR = Path(__file__).resolve().parent / "quiz_banks"


async def seed_from_json_banks(banks_dir: Path = _DEFAULT_BANKS_DIR) -> int:
    """Insert questions from JSON seed files for skills that have an empty bank.

    Args:
        banks_dir: Directory containing ``<skill_slug>.json`` files.
                   Defaults to ``backend/seeds/quiz_banks/``.

    Returns:
        Number of skills whose banks were seeded (0 if all already populated).
    """
    if not banks_dir.exists():
        logger.debug("[SeedLoader] No seed directory found at %s — skipping.", banks_dir)
        return 0

    seed_files = sorted(banks_dir.glob("*.json"))
    if not seed_files:
        logger.debug("[SeedLoader] Seed directory is empty — skipping.")
        return 0

    seeded_skills = 0
    total_questions = 0
    now = datetime.now(UTC)

    for seed_path in seed_files:
        try:
            payload = json.loads(seed_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("[SeedLoader] Could not read %s: %s", seed_path.name, exc)
            continue

        skill_key: str = payload.get("skill_key", "")
        skill_label: str = payload.get("skill", skill_key)
        questions: list = payload.get("questions", [])

        if not skill_key or not questions:
            logger.warning("[SeedLoader] %s has no skill_key or questions — skipped.", seed_path.name)
            continue

        # Check whether the skill already has questions in the DB.
        async with async_session() as session:
            stmt = select(func.count()).where(
                SkillQuestion.skill == skill_key,
                SkillQuestion.active.is_(True),
            )
            count = int((await session.execute(stmt)).scalar_one() or 0)

        if count > 0:
            # Already populated — skip to avoid duplicates.
            continue

        # Bulk-insert all questions from the seed file.
        rows = []
        for q in questions:
            q_text = str(q.get("question", "")).strip()
            options = q.get("options", [])
            correct_index = q.get("correct_index", 0)
            if not q_text or not options:
                continue
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "skill": skill_key,
                    "skill_label": skill_label,
                    "question": q_text,
                    "options": options,
                    "correct_index": int(correct_index),
                    "reviewed": True,  # seed questions are considered reviewed
                    "active": True,
                    "source": "seed",
                    "review_note": "",
                    "created_at": now,
                    "updated_at": now,
                }
            )

        if not rows:
            continue

        async with async_session() as session:
            dialect = session.bind.dialect.name if session.bind else "postgresql"
            if dialect == "postgresql":
                # Bulk upsert — skip duplicates silently.
                stmt = pg_insert(SkillQuestion).values(rows).on_conflict_do_nothing(index_elements=["id"])
                await session.execute(stmt)
            else:
                # SQLite (dev / tests): plain INSERT ignoring conflicts.
                from sqlalchemy.dialects.sqlite import insert as sqlite_insert
                stmt = sqlite_insert(SkillQuestion).values(rows).prefix_with("OR IGNORE")
                await session.execute(stmt)
            await session.commit()

        seeded_skills += 1
        total_questions += len(rows)

    if seeded_skills:
        logger.info(
            "[SeedLoader] Seeded %d skills from JSON banks (%d questions total).",
            seeded_skills,
            total_questions,
        )
    else:
        logger.debug("[SeedLoader] All skill banks already populated — no seeding needed.")

    return seeded_skills

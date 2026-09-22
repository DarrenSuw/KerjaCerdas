"""One-time export: dump up to 30 quiz questions per skill from Postgres to JSON seed files.

Usage (from repo root):
    .\\backend\\venv\\Scripts\\python.exe -m backend.scripts.export_quiz_banks

Output: backend/seeds/quiz_banks/<skill_slug>.json — one file per skill.

The 30 questions are chosen by `created_at ASC` (oldest first). If a
`quality_score` column is ever added, swap the ORDER BY here.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap — allow running as `python -m backend.scripts.export_quiz_banks`
# from the repo root without installing the package.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.app.api.database import engine, init_db  # noqa: E402
from backend.app.db.models_proof import SkillQuestion  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

EXPORT_LIMIT = 30
# __file__ = backend/scripts/export_quiz_banks.py
# parents[0] = backend/scripts/
# parents[1] = backend/
SEEDS_DIR = Path(__file__).resolve().parents[1] / "seeds" / "quiz_banks"


def _slug(text: str) -> str:
    """Convert a skill name or skill key to a safe filename slug."""
    s = text.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s or "unknown"


async def export_banks() -> None:
    SEEDS_DIR.mkdir(parents=True, exist_ok=True)

    await init_db()

    from backend.app.db.session import async_session

    # ------------------------------------------------------------------
    # 1. Enumerate all distinct skills that have at least one active
    #    question (reviewed or draft — we want reviewed ones for the seed).
    # ------------------------------------------------------------------
    async with async_session() as session:
        skills_stmt = (
            select(
                SkillQuestion.skill,
                func.max(SkillQuestion.skill_label),
            )
            .where(SkillQuestion.active.is_(True))
            .group_by(SkillQuestion.skill)
        )
        skill_rows = (await session.execute(skills_stmt)).all()

    skills = [(r[0], r[1] or r[0]) for r in skill_rows]
    logger.info("Found %d distinct skills in the database.", len(skills))

    total_questions = 0
    exported_skills = 0

    for skill_key, skill_label in skills:
        async with async_session() as session:
            # Prefer reviewed=True rows; take first 30 by created_at.
            stmt = (
                select(
                    SkillQuestion.question,
                    SkillQuestion.options,
                    SkillQuestion.correct_index,
                )
                .where(
                    SkillQuestion.skill == skill_key,
                    SkillQuestion.active.is_(True),
                    SkillQuestion.reviewed.is_(True),
                )
                .order_by(SkillQuestion.created_at.asc())
                .limit(EXPORT_LIMIT)
            )
            rows = (await session.execute(stmt)).all()

        if not rows:
            # Fall back to unreviewed active rows if there are no reviewed ones.
            async with async_session() as session:
                stmt = (
                    select(
                        SkillQuestion.question,
                        SkillQuestion.options,
                        SkillQuestion.correct_index,
                    )
                    .where(
                        SkillQuestion.skill == skill_key,
                        SkillQuestion.active.is_(True),
                    )
                    .order_by(SkillQuestion.created_at.asc())
                    .limit(EXPORT_LIMIT)
                )
                rows = (await session.execute(stmt)).all()

        if not rows:
            logger.warning("Skill '%s' has no questions to export — skipped.", skill_key)
            continue

        questions = []
        for q, opts, ci in rows:
            # Normalise: options must be a list of strings.
            if isinstance(opts, str):
                try:
                    opts = json.loads(opts)
                except Exception:
                    opts = [opts]
            questions.append(
                {
                    "question": q,
                    "options": [str(o) for o in (opts or [])],
                    "correct_index": int(ci) if ci is not None else 0,
                }
            )

        payload = {
            "skill": skill_label,
            "skill_key": skill_key,
            "questions": questions,
        }

        out_path = SEEDS_DIR / f"{_slug(skill_key)}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        exported_skills += 1
        total_questions += len(questions)
        logger.info(
            "  [%3d] %-40s → %d questions → %s",
            exported_skills,
            skill_label[:40],
            len(questions),
            out_path.name,
        )

    logger.info(
        "\nExport complete: %d skills, %d questions → %s",
        exported_skills,
        total_questions,
        SEEDS_DIR,
    )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(export_banks())

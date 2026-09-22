#!/usr/bin/env python3
"""Audit a random sample of stored quiz questions for answer-key integrity.

This script checks the persisted rows when a database is available, and falls
back to the canonical starter-bank source when no dev database is running.
"""

from __future__ import annotations

import asyncio
import random
from collections import defaultdict

from sqlalchemy import select

from backend.app.api.database import async_session_factory
from backend.app.db.models_proof import SkillQuestion
from backend.app.services.quiz.bank_data import BANK


def _normalize_option(value: object) -> str:
    return str(value).strip()


def _validate_question_record(skill: str, question: str, options: list[str], correct: int) -> list[str]:
    issues: list[str] = []
    cleaned = [_normalize_option(o) for o in (options or [])]

    if not isinstance(correct, int):
        return [f"{skill}: correct_index is not an int ({type(correct).__name__})"]
    if not 0 <= correct < 4:
        return [f"{skill}: correct_index out of range ({correct})"]
    if len(cleaned) != 4:
        return [f"{skill}: option count is {len(cleaned)}, expected 4"]
    if any(not opt for opt in cleaned):
        issues.append(f"{skill}: empty option detected")
    if len({opt.casefold() for opt in cleaned}) != 4:
        issues.append(f"{skill}: duplicate or near-duplicate options after trimming")

    target = cleaned[correct]
    matches = [idx for idx, opt in enumerate(cleaned) if opt == target]
    if len(matches) != 1:
        issues.append(
            f"{skill}: correct_index {correct} maps to {target!r}, which matches {len(matches)} options"
        )
    if not question.strip():
        issues.append(f"{skill}: empty question text")

    return issues


def _sample_bank_records() -> list[tuple[str, str, list[str], int]]:
    rng = random.Random(42)
    grouped: dict[str, list[tuple[str, str, list[str], int]]] = defaultdict(list)
    for skill_key, skill_label, question, options, correct in BANK:
        grouped[skill_key].append((skill_key, question, [str(o).strip() for o in options], int(correct)))

    chosen: list[tuple[str, str, list[str], int]] = []
    skills = list(grouped)
    rng.shuffle(skills)
    for skill in skills:
        pool = grouped[skill]
        if not pool:
            continue
        for item in rng.sample(pool, min(len(pool), 2)):
            chosen.append(item)
            if len(chosen) >= 15:
                return chosen
    return chosen[:15]


async def _sample_db_records() -> list[tuple[str, str, list[str], int]]:
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(SkillQuestion).where(SkillQuestion.active.is_(True), SkillQuestion.reviewed.is_(True))
            )
            rows = result.scalars().all()
    except Exception:  # noqa: BLE001
        return _sample_bank_records()

    if not rows:
        return _sample_bank_records()

    by_skill: dict[str, list[SkillQuestion]] = defaultdict(list)
    for row in rows:
        by_skill.setdefault(row.skill, []).append(row)

    chosen: list[tuple[str, str, list[str], int]] = []
    rng = random.Random(42)
    skill_names = list(by_skill)
    rng.shuffle(skill_names)
    for skill in skill_names:
        pool = by_skill[skill]
        if not pool:
            continue
        sample_count = min(len(pool), 2)
        for row in rng.sample(pool, sample_count):
            chosen.append((row.skill, row.question, [str(o).strip() for o in row.options], int(row.correct_index)))
            if len(chosen) >= 15:
                return chosen
    return chosen[:15]


async def main() -> int:
    records = await _sample_db_records()
    issues: list[str] = []
    for skill, question, options, correct in records:
        issues.extend(_validate_question_record(skill, question, options, correct))

    if issues:
        print(f"Malformed questions found: {len(issues)}")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print(f"Validated {len(records)} sampled questions across {len({skill for skill, *_ in records})} skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

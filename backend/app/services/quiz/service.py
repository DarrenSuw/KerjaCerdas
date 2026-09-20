"""Skill quiz engine: 5 random questions, 45 s each, pass = 4/5 correct.

Grading uses the answer key only (no AI call per attempt, so a quiz costs Rp0
to run). Passing sets the skill's proof level to "quiz" for 180 days
(services/matching/evidence.py), which raises the proof-weighted part of the
match score at every employer.

Question sources (in priority order):
  1. Static starter bank (bank_data.py) — 8 entry-level skills, seeded once.
  2. AI-generated questions (generator.py) — when a skill has no bank entry,
     Gemini generates 6 scenario questions + answer keys on first request.
     Generated questions are stored in the DB with `reviewed=False` and graded
     by the same answer-key engine, keeping per-attempt cost at Rp0. The
     generation cost (~Rp60-130) is paid once per skill.

Anti-cheating is honest, not absolute: random questions and option order per
attempt, a server-side deadline, answers never sent before submission, and a
retake cooldown after a failed attempt. The interview (and HR's "terbukti"
tick) is the final check.
"""

from __future__ import annotations

import random
import secrets
from datetime import UTC, date, datetime, timedelta

from backend.app.db import postgres_store as store
from backend.app.db.schemas import SeekerProfile, Skill
from backend.app.db.schemas_proof import QuizAttempt, SkillEvidence
from backend.app.services.matching.evidence import skill_key

QUESTIONS_PER_QUIZ = 5
SECONDS_PER_QUESTION = 45
PASS_MARK = 4
GRACE_SECONDS = 15
RETAKE_DAYS_FREE = 7
RETAKE_DAYS_PRISM = 2


class QuizError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def option_order(attempt_id: str, question_id: str, n_options: int) -> list[int]:
    """Deterministic per-attempt shuffle: displayed position -> original index."""
    order = list(range(n_options))
    random.Random(f"{attempt_id}:{question_id}").shuffle(order)
    return order


async def seed_bank_if_empty() -> int:
    """Insert the starter bank once. Returns the number of questions inserted."""
    from backend.app.db.schemas_proof import SkillQuestion
    from backend.app.services.quiz.bank_data import BANK

    repos = store.get_repositories()
    if await store.list_quiz_skills():
        return 0
    for key, label, question, options, correct in BANK:
        await repos.skill_questions.upsert(
            SkillQuestion(
                skill=key,
                skill_label=label,
                question=question,
                options=options,
                correct_index=correct,
                reviewed=True,
            )
        )
    return len(BANK)


def _public_questions(attempt: QuizAttempt, questions: dict) -> list[dict]:
    out = []
    for qid in attempt.question_ids:
        q = questions[qid]
        order = option_order(attempt.id, qid, len(q.options))
        out.append({"id": qid, "question": q.question, "options": [q.options[i] for i in order]})
    return out


async def start_quiz(seeker: SeekerProfile, skill_name: str, prism: bool) -> dict:
    key = skill_key(skill_name)
    bank = await store.find_active_questions(key)

    # If insufficient questions, attempt AI generation (Option B: generate once
    # with answer key, grade for free on every future attempt).
    if len(bank) < QUESTIONS_PER_QUIZ:
        from backend.app.services.quiz.generator import GenerationError, ensure_questions_exist

        try:
            generated = await ensure_questions_exist(skill_name, min_count=QUESTIONS_PER_QUIZ)
            if generated:
                bank = await store.find_active_questions(key)
        except GenerationError as exc:
            # If AI generation also fails, surface the reason
            if len(bank) < QUESTIONS_PER_QUIZ:
                raise QuizError(404, f"Belum ada kuis untuk skill '{skill_name}'. {exc.args[0]}")

    if len(bank) < QUESTIONS_PER_QUIZ:
        raise QuizError(404, f"Belum ada kuis untuk skill '{skill_name}'.")

    now = datetime.now(UTC)
    attempts = await store.find_quiz_attempts(seeker.id, key)
    for a in attempts:  # resume an open attempt instead of drawing new questions
        if a.submitted_at is None and _aware(a.deadline_at) > now:
            by_id = {q.id: q for q in bank}
            if all(qid in by_id for qid in a.question_ids):
                return _attempt_payload(a, by_id, resumed=True)

    cooldown = RETAKE_DAYS_PRISM if prism else RETAKE_DAYS_FREE
    failed = [a for a in attempts if a.submitted_at and not a.passed]
    if failed:
        retry_at = _aware(failed[-1].submitted_at) + timedelta(days=cooldown)
        if retry_at > now:
            raise QuizError(429, f"Kamu bisa mengulang kuis ini mulai {retry_at.date().isoformat()}.")

    picked = secrets.SystemRandom().sample(bank, QUESTIONS_PER_QUIZ)
    attempt = QuizAttempt(
        seeker_id=seeker.id,
        skill=key,
        question_ids=[q.id for q in picked],
        deadline_at=now + timedelta(seconds=SECONDS_PER_QUESTION * QUESTIONS_PER_QUIZ),
    )
    await store.get_repositories().quiz_attempts.upsert(attempt)
    return _attempt_payload(attempt, {q.id: q for q in picked}, resumed=False)


def _attempt_payload(attempt: QuizAttempt, by_id: dict, resumed: bool) -> dict:
    label = next(iter(by_id.values())).skill_label if by_id else attempt.skill
    return {
        "attempt_id": attempt.id,
        "skill": attempt.skill,
        "skill_label": label,
        "deadline_at": _aware(attempt.deadline_at).isoformat(),
        "seconds_per_question": SECONDS_PER_QUESTION,
        "pass_mark": PASS_MARK,
        "resumed": resumed,
        "draft_bank": not all(q.reviewed for q in by_id.values()),
        "questions": _public_questions(attempt, by_id),
    }


async def submit_quiz(seeker: SeekerProfile, attempt_id: str, answers: list[int]) -> dict:
    repos = store.get_repositories()
    attempt = await repos.quiz_attempts.get(attempt_id)
    if not attempt or attempt.seeker_id != seeker.id:
        raise QuizError(404, "Kuis tidak ditemukan.")
    if attempt.submitted_at is not None:
        raise QuizError(409, "Kuis ini sudah dikumpulkan.")

    now = datetime.now(UTC)
    late = now > _aware(attempt.deadline_at) + timedelta(seconds=GRACE_SECONDS)
    by_id = {q.id: q for q in await store.find_active_questions(attempt.skill)}
    correct_flags: list[bool] = []
    for i, qid in enumerate(attempt.question_ids):
        q = by_id.get(qid)
        chosen = answers[i] if i < len(answers) else -1
        ok = False
        if q is not None and not late and 0 <= chosen < len(q.options):
            ok = option_order(attempt.id, qid, len(q.options))[chosen] == q.correct_index
        correct_flags.append(ok)

    score = sum(correct_flags)
    attempt.answers = [int(a) for a in answers[: len(attempt.question_ids)]]
    attempt.submitted_at = now
    attempt.score = score
    attempt.passed = score >= PASS_MARK
    await repos.quiz_attempts.upsert(attempt)

    if attempt.passed:
        await _record_pass(seeker, attempt)

    return {
        "attempt_id": attempt.id,
        "skill": attempt.skill,
        "score": score,
        "total": len(attempt.question_ids),
        "passed": attempt.passed,
        "late": late,
        "correct": correct_flags,  # which were right — never which option was right
        "retake_after_days": None if attempt.passed else RETAKE_DAYS_FREE,
    }


async def _record_pass(seeker: SeekerProfile, attempt: QuizAttempt) -> None:
    repos = store.get_repositories()
    await repos.skill_evidence.upsert(
        SkillEvidence(seeker_id=seeker.id, skill=attempt.skill, source="quiz", source_id=attempt.id)
    )
    today = date.today().isoformat()
    label = attempt.skill
    bank = await store.find_active_questions(attempt.skill)
    if bank:
        label = bank[0].skill_label or label

    fresh = await repos.seekers.get(seeker.id) or seeker
    updated = False
    for sk in fresh.skills:
        if skill_key(sk.name) == attempt.skill:
            if sk.proof_level != "hr_confirmed":
                sk.proof_level = "quiz"
                sk.proof_date = today
            updated = True
    if not updated:
        fresh.skills.append(Skill(name=label, proof_level="quiz", proof_date=today))
    fresh.updated_at = datetime.now(UTC)
    await repos.seekers.upsert(fresh)

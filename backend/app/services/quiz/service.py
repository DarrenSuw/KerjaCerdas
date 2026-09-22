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

import logging
import random
import secrets
from datetime import UTC, date, datetime, timedelta

from backend.app.db import postgres_store as store
from backend.app.db.schemas import SeekerProfile, Skill
from backend.app.db.schemas_proof import QuizAttempt, SkillEvidence
from backend.app.services.matching.evidence import skill_key

logger = logging.getLogger(__name__)

QUESTIONS_PER_QUIZ = 5
SECONDS_PER_QUESTION = 45
PASS_MARK = 4
GRACE_SECONDS = 15
ABANDON_AFTER_SECONDS = 30
# Exactly one attempt per skill per day, regardless of pass or fail.
# Retake resistance comes from bank size (generator.BANK_TARGET=50) plus
# non-overlapping random draws (_pick_questions). With a 50-question pool and
# 5 drawn per attempt, the chance of drawing the exact same 5 twice is <0.1%.
RETAKE_DAYS = 1
# Cap: any submitted attempt (pass or fail) within the last RETAKE_DAYS days
# blocks a new start. This is evaluated in start_quiz() below.
_ATTEMPT_CAP_PER_PERIOD = 1


class QuizError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


# Per-skill cooldown for non-critical top-ups. In-process and lost on restart,
# which is the right trade: the cost it bounds is a burst of calls within one
# session, and a durable marker would need a table for a rate limit.
_TOPUP_COOLDOWN_S = 6 * 3600
# A bank too small to run a quiz still gets throttled, just far more loosely.
# Exempting it entirely (the first version of this) left the expensive path
# wide open: a seeker who claims a skill the generator keeps failing on could
# hammer /quiz/start and pay for a generation attempt on every request.
_COLD_COOLDOWN_S = 15 * 60
_last_topup: dict[str, float] = {}


# Cold-start generations one account may trigger per day, across ALL skills.
# The per-skill throttle alone does not bound cost: adding a skill to a profile
# is free and unlimited, so an attacker claims fifty invented skills and gets
# fifty generations per window. The gate has to count the PAYER's requests, not
# the skill's.
GENERATIONS_PER_USER_PER_DAY = 3


async def _generation_budget_left(user_id: str) -> bool:
    from datetime import datetime as _dt

    from backend.app.db.postgres_store import consume_quota

    since = _dt.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return await consume_quota(
        user_id, "quiz_generation", GENERATIONS_PER_USER_PER_DAY, since
    )


def _topup_allowed(key: str, *, serveable: bool) -> bool:
    """Throttle paid generation per skill. Cold banks retry sooner, not freely."""
    import time

    window = _TOPUP_COOLDOWN_S if serveable else _COLD_COOLDOWN_S
    now = time.monotonic()
    if now - _last_topup.get(key, -window) < window:
        return False
    _last_topup[key] = now
    return True


def generator_target() -> int:
    from backend.app.services.quiz.generator import BANK_TARGET

    return BANK_TARGET


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


async def start_quiz(seeker: SeekerProfile, skill_name: str) -> dict:
    key = skill_key(skill_name)

    bank = await store.find_active_questions(key)

    # Generation — not the quiz itself — is the expensive, abusable action, so
    # the profile check gates only that. Any skill that already has a bank stays
    # open to everyone: taking a quiz for a skill you have not listed yet is how
    # you earn it, and costs Rp0. But a skill with NO bank would have us pay
    # Gemini ~Rp85-130 on demand, so an invented name must not reach it — that
    # was a free money burner any logged-in user could loop.
    claimed = {skill_key(s.name) for s in (seeker.skills or []) if s.name}
    if not bank and key not in claimed:
        raise QuizError(
            400,
            f"Kuis untuk skill '{skill_name}' belum ada. Tambahkan skill ini ke "
            "profilmu dulu kalau memang kamu kuasai, lalu coba lagi.",
        )

    # Top the bank up toward BANK_TARGET whenever it is short. A thin bank is
    # what lets a retake repeat questions, so refilling is a correctness fix,
    # not a nicety — see generator.BANK_TARGET. Once the bank is serveable the
    # top-up is rate-limited per skill: a partially-filled bank must not pay for
    # a generation attempt on every single quiz start.
    # A retake cannot honour the no-repeat rule below 2x the quiz length, so a
    # bank in that range is treated as urgently as an empty one rather than
    # waiting out the six-hour top-up window with a candidate stuck repeating
    # questions. Guard: TestReviewFindingsStayFixed.
    attempts_so_far = await store.find_quiz_attempts(seeker.id, key)
    needs_refill_now = len(bank) < QUESTIONS_PER_QUIZ or (
        len(bank) < 2 * QUESTIONS_PER_QUIZ
        and any(a.submitted_at is not None for a in attempts_so_far)
    )

    if (
        len(bank) < generator_target()
        and _topup_allowed(key, serveable=not needs_refill_now)
        and await _generation_budget_left(seeker.user_id)
    ):
        from backend.app.services.quiz.generator import GenerationError, ensure_questions_exist

        try:
            if await ensure_questions_exist(skill_name):
                bank = await store.find_active_questions(key)
        except GenerationError as exc:
            # Re-read: a batch may have landed before the failure, and judging
            # the pre-generation list here would tell a seeker the quiz is
            # unavailable while enough questions now exist to run it.
            bank = await store.find_active_questions(key)
            # A top-up failure on an already-serveable bank must not block the
            # quiz; only an unusable bank is fatal.
            if len(bank) < QUESTIONS_PER_QUIZ:
                await store.add_event(seeker.user_id, "quiz_unavailable", {"skill": key})
                raise QuizError(
                    503,
                    f"Kuis untuk skill '{skill_name}' belum siap. {exc.args[0]} "
                    "Skill ini tetap tercatat sebagai klaim di profilmu.",
                ) from exc

    if len(bank) < QUESTIONS_PER_QUIZ:
        await store.add_event(seeker.user_id, "quiz_unavailable", {"skill": key})
        raise QuizError(
            503,
            f"Kuis untuk skill '{skill_name}' sedang disiapkan. Skill ini tetap "
            "tercatat sebagai klaim di profilmu.",
        )

    now = datetime.now(UTC)
    attempts = await store.find_quiz_attempts(seeker.id, key)
    for a in attempts:  # resume an open attempt instead of drawing new questions
        if a.submitted_at is None and _aware(a.deadline_at) > now:
            by_id = {q.id: q for q in bank}
            if all(qid in by_id for qid in a.question_ids):
                return _attempt_payload(a, by_id, resumed=True)

    # 1 attempt per RETAKE_DAYS day(s), pass or fail. Checks the most recent
    # *submitted* attempt regardless of outcome so passing on Monday doesn't
    # let you grind the same skill all week.
    submitted_all = sorted(
        [a for a in attempts if a.submitted_at is not None],
        key=lambda a: _aware(a.submitted_at),
    )
    if len(submitted_all) >= _ATTEMPT_CAP_PER_PERIOD:
        last_submit = _aware(submitted_all[-1].submitted_at)
        retry_at = last_submit + timedelta(days=RETAKE_DAYS)
        if retry_at > now:
            raise QuizError(429, f"Kamu bisa mengulang kuis ini mulai {retry_at.date().isoformat()}.")

    picked = _pick_questions(bank, attempts)
    previous = next(
        (a.question_ids or [] for a in reversed(attempts) if a.submitted_at is not None), []
    )
    repeated = len({q.id for q in picked} & set(previous))
    if repeated:
        # The contract is "a retake never repeats"; a bank this thin cannot keep
        # it. Two bad options, and we take neither: refusing the quiz punishes
        # the candidate for OUR unfinished bank, while awarding a badge for
        # questions they were shown yesterday hands out proof that was not
        # earned — and that badge carries a 0.85 weight straight into the match
        # score. So the attempt runs, is scored, and gives feedback, but it
        # cannot grant proof. Reporting the overlap was not enough: visibility
        # is not mitigation when the harm is the badge itself.
        logger.warning(
            "Bank '%s' too small to honour no-repeat: %d of %d questions reused; "
            "attempt will not be proof-bearing",
            key, repeated, QUESTIONS_PER_QUIZ,
        )
    attempt = QuizAttempt(
        seeker_id=seeker.id,
        skill=key,
        question_ids=[q.id for q in picked],
        deadline_at=now + timedelta(seconds=SECONDS_PER_QUESTION * QUESTIONS_PER_QUIZ),
        proof_eligible=not repeated,
    )
    await store.get_repositories().quiz_attempts.upsert(attempt)
    payload = _attempt_payload(attempt, {q.id: q for q in picked}, resumed=False)
    payload["repeated_questions"] = repeated
    payload["proof_eligible"] = attempt.proof_eligible
    if not attempt.proof_eligible:
        payload["notice"] = (
            f"Bank soal untuk skill ini belum cukup besar, jadi {repeated} soal "
            "terpaksa diulang dari percobaan sebelumnya. Kuis ini tetap bisa kamu "
            "kerjakan dan hasilnya tetap kami tampilkan, tapi **belum bisa memberi "
            "badge terbukti** — lulus atas soal yang sudah kamu lihat bukan bukti. "
            "Kami sedang menambah soalnya; coba lagi nanti untuk kuis penuh."
        )
    return payload


def _pick_questions(bank: list, attempts: list) -> list:
    """Draw QUESTIONS_PER_QUIZ questions, avoiding what this seeker just saw.

    Rule 1 (hard): nothing from the immediately previous submitted attempt. With
    a 6-question bank the old uniform sample repeated at least 4 of 5 on every
    retake, so a badge was obtainable by memorising six items — while feeding a
    0.85 proof weight.

    Rule 2 (preference): also avoid the attempt before that, when the bank is
    large enough to still leave a real choice. Applied only if it does, because
    forcing it on a thin bank would make the draw deterministic, which is the
    very predictability the rule exists to prevent.

    Never raises on a small bank. A seeker must not be locked out of a retake
    because we have not finished writing questions.
    """
    submitted = [a for a in attempts if a.submitted_at is not None]
    submitted.sort(key=lambda a: _aware(a.submitted_at))
    rng = secrets.SystemRandom()

    def _exclude(n_attempts: int) -> list:
        blocked: set[str] = set()
        for a in submitted[-n_attempts:] if n_attempts else []:
            blocked.update(a.question_ids or [])
        return [q for q in bank if q.id not in blocked]

    # Depths 2 and 1 only. A depth of 0 excludes nothing, so it would always
    # succeed for any bank of 5 or more and return a uniform sample — which made
    # the least-recently-seen fallback below unreachable and let a retake redraw
    # yesterday's questions at random. start_quiz guarantees len(bank) >= 5, so
    # dropping depth 0 cannot leave the draw short.
    for depth in (2, 1):
        pool = _exclude(depth)
        if len(pool) >= QUESTIONS_PER_QUIZ:
            return rng.sample(pool, QUESTIONS_PER_QUIZ)

    # Bank too small to honour the rule. Serve anyway — locking a candidate out
    # of a retake because WE have not finished writing questions is the worse
    # failure — but fill the unavoidable remainder with the questions seen
    # LONGEST ago rather than drawing blind, so the overlap is as small and as
    # stale as the bank allows instead of being random.
    last_seen: dict[str, int] = {}
    for order, att in enumerate(submitted):
        for qid in att.question_ids or []:
            last_seen[qid] = order
    fresh = _exclude(1)
    rng.shuffle(fresh)
    stale = sorted(
        (q for q in bank if q not in fresh), key=lambda q: last_seen.get(q.id, -1)
    )
    return (fresh + stale)[:QUESTIONS_PER_QUIZ]


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
        return {
            "attempt_id": attempt.id,
            "skill": attempt.skill,
            "score": attempt.score or 0,
            "total": len(attempt.question_ids),
            "passed": bool(attempt.passed),
            "late": attempt.status == "abandoned",
            "correct": [],
            "proof_granted": bool(attempt.passed and getattr(attempt, "proof_eligible", True)),
            "retake_after_days": None if attempt.passed else RETAKE_DAYS,
        }

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
    attempt.status = "submitted"
    attempt.score = score
    attempt.passed = score >= PASS_MARK
    await repos.quiz_attempts.upsert(attempt)

    # A pass on a compromised draw is real feedback but not evidence, so it is
    # never written to skill_evidence and never lifts proof_level.
    if attempt.passed and getattr(attempt, "proof_eligible", True):
        await _record_pass(seeker, attempt)

    return {
        "attempt_id": attempt.id,
        "skill": attempt.skill,
        "score": score,
        "total": len(attempt.question_ids),
        "passed": attempt.passed,
        "late": late,
        "correct": correct_flags,  # which were right — never which option was right
        "proof_granted": bool(attempt.passed and getattr(attempt, "proof_eligible", True)),
        "retake_after_days": None if attempt.passed else RETAKE_DAYS,
    }


async def abandon_quiz(seeker: SeekerProfile, attempt_id: str, elapsed_seconds: int | None = None) -> dict:
    repos = store.get_repositories()
    attempt = await repos.quiz_attempts.get(attempt_id)
    if not attempt or attempt.seeker_id != seeker.id:
        raise QuizError(404, "Kuis tidak ditemukan.")
    if attempt.submitted_at is not None:
        return {"attempt_id": attempt.id, "status": getattr(attempt, "status", "submitted") or "submitted", "used_attempt": False}

    now = datetime.now(UTC)
    elapsed = max(0, int(elapsed_seconds)) if elapsed_seconds is not None else int((now - _aware(attempt.created_at)).total_seconds())
    if elapsed < ABANDON_AFTER_SECONDS:
        return {"attempt_id": attempt.id, "status": "in_progress", "used_attempt": False}

    attempt.answers = [int(a) for a in getattr(attempt, "answers", []) or []]
    attempt.submitted_at = now
    attempt.status = "abandoned"
    attempt.score = 0
    attempt.passed = False
    await repos.quiz_attempts.upsert(attempt)
    return {
        "attempt_id": attempt.id,
        "status": "abandoned",
        "used_attempt": True,
        "elapsed_seconds": elapsed,
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

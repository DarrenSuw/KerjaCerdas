"""Skill quizzes — how a job seeker proves a skill (✓ Terbukti badge).

GET  /quiz/skills?job_id=   skills with a quiz, and this seeker's proof status
POST /quiz/start            {skill}                -> 5 questions, no answers
POST /quiz/submit           {attempt_id, answers}  -> score, passed
"""

from __future__ import annotations

from backend.app.api.dependencies import get_current_user, require_seeker
from backend.app.db.models import User
from backend.app.db.postgres_store import find_seeker_by_user_id, get_repositories, list_quiz_skills
from backend.app.services.billing.plans import entitlements_for
from backend.app.services.matching.evidence import effective_proof, skill_key
from backend.app.services.quiz import service as quiz
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/quiz", tags=["quiz"], dependencies=[Depends(require_seeker)])


class StartReq(BaseModel):
    skill: str = Field(min_length=1, max_length=120)


class SubmitReq(BaseModel):
    attempt_id: str = Field(max_length=64)
    answers: list[int] = Field(max_length=10)


async def _seeker(user: User):
    seeker = await find_seeker_by_user_id(user.id)
    if not seeker:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Buat profil dulu sebelum mengikuti kuis.")
    return seeker


@router.get("/skills")
async def quiz_skills(job_id: str | None = None, current_user: User = Depends(get_current_user)):
    seeker = await find_seeker_by_user_id(current_user.id)
    bank = {row["skill"]: row for row in await list_quiz_skills()}
    held = {}
    for sk in seeker.skills if seeker else []:
        held[skill_key(sk.name)] = {"name": sk.name, "proof": effective_proof(sk),
                                    "proof_date": sk.proof_date}

    wanted: list[str] = []
    if job_id:
        job = await get_repositories().jobs.get(job_id)
        if job:
            wanted = list(job.required_skills or [])
    names = wanted or [h["name"] for h in held.values()] or [r["label"] for r in bank.values()]

    items, seen = [], set()
    for name in names:
        key = skill_key(name)
        if key in seen:
            continue
        seen.add(key)
        items.append({
            "skill": name,
            "key": key,
            "quiz_available": key in bank,
            "proof": held.get(key, {}).get("proof", "missing" if job_id else "claimed"),
            "proof_date": held.get(key, {}).get("proof_date"),
        })
    return {"items": items, "bank": list(bank.values()), "pass_mark": quiz.PASS_MARK,
            "questions_per_quiz": quiz.QUESTIONS_PER_QUIZ}


@router.post("/start")
async def start(req: StartReq, current_user: User = Depends(get_current_user)):
    seeker = await _seeker(current_user)
    ent = await entitlements_for(current_user.id)
    try:
        return await quiz.start_quiz(seeker, req.skill, prism=ent.has_prism)
    except quiz.QuizError as exc:
        raise HTTPException(exc.status, exc.message) from exc


@router.post("/submit")
async def submit(req: SubmitReq, current_user: User = Depends(get_current_user)):
    seeker = await _seeker(current_user)
    try:
        result = await quiz.submit_quiz(seeker, req.attempt_id, req.answers)
    except quiz.QuizError as exc:
        raise HTTPException(exc.status, exc.message) from exc
    if not result["passed"]:
        ent = await entitlements_for(current_user.id)
        result["retake_after_days"] = (
            quiz.RETAKE_DAYS_PRISM if ent.has_prism else quiz.RETAKE_DAYS_FREE
        )
    return result

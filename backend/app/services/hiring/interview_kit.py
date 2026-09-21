"""Interview questions per candidate, focused on skills that are only claimed.

"Kuis menyaring, wawancara memastikan": quizzes filter, the interview confirms.
For every required skill the candidate has NOT proven (claimed or missing) we
ask a practical question; for quiz-proven skills we ask them to explain a
real example, which exposes anyone whose quiz was answered by someone else.

Uses the chat LLM when configured (PII is redacted centrally in llm_factory);
otherwise falls back to deterministic templates so the feature always works.
"""

from __future__ import annotations

import logging

from backend.app.db.schemas import JobPosting, SeekerProfile
from backend.app.services.matching.evidence import skill_proof_view

logger = logging.getLogger(__name__)

MAX_QUESTIONS = 5

_TEMPLATES = {
    "claimed": "Ceritakan satu situasi nyata saat kamu memakai {skill}. Apa yang kamu lakukan dan apa hasilnya?",
    "missing": "Posisi ini membutuhkan {skill}. Bagaimana kamu akan mempelajarinya di bulan pertama?",
    "quiz": "Kamu lulus kuis {skill}. Beri contoh kasus kerja di mana kamu menerapkannya, langkah demi langkah.",
}


def template_kit(job: JobPosting, seeker: SeekerProfile) -> list[dict]:
    view = skill_proof_view(seeker.skills, job.required_skills)
    order = {"claimed": 0, "missing": 1, "quiz": 2, "hr_confirmed": 3}
    questions = []
    for item in sorted(view, key=lambda v: order.get(v["status"], 9)):
        if item["status"] == "hr_confirmed":
            continue
        questions.append({
            "skill": item["name"],
            "proof": item["status"],
            "question": _TEMPLATES[item["status"]].format(skill=item["name"]),
        })
        if len(questions) >= MAX_QUESTIONS:
            break
    if not questions:
        questions.append({"skill": "", "proof": "hr_confirmed",
                          "question": f"Apa yang membuatmu tertarik dengan posisi {job.title}?"})
    return questions


async def build_kit(job: JobPosting, seeker: SeekerProfile) -> dict:
    base = template_kit(job, seeker)
    from backend.app.services.llm_factory import build_chat_llm, resolve_gemini_key

    if not resolve_gemini_key():
        return {"source": "template", "questions": base}
    try:
        from langchain_core.messages import HumanMessage

        from backend.app.utils import content_to_text

        focus = "; ".join(f"{q['skill']} ({q['proof']})" for q in base if q["skill"])
        prompt = (
            "Kamu membantu HR usaha kecil menyiapkan wawancara. Buat maksimal "
            f"{MAX_QUESTIONS} pertanyaan wawancara praktis dalam Bahasa Indonesia, satu per baris, "
            "tanpa nomor, untuk menguji apakah kandidat benar-benar menguasai skill berikut. "
            "Status 'claimed' = hanya ditulis di CV, 'missing' = belum dimiliki, "
            "'quiz' = lulus kuis (minta contoh nyata).\n"
            f"Posisi: {job.title}\nSkill: {focus}"
        )
        resp = await build_chat_llm(temperature=0.3, task="interview_kit").ainvoke([HumanMessage(content=prompt)])
        lines = [ln.strip(" -•\t") for ln in content_to_text(resp.content).splitlines() if ln.strip()]
        if lines:
            qs = [{"skill": "", "proof": "", "question": ln} for ln in lines[:MAX_QUESTIONS]]
            return {"source": "ai", "questions": qs, "focus": base}
    except Exception as exc:  # noqa: BLE001 — degrade to templates
        logger.warning("Interview kit AI generation failed: %s", exc)
    return {"source": "template", "questions": base}

"""AI-powered quiz question generator — Option B: generate once with answer key.

When a seeker starts a quiz for a skill that has no questions in the bank,
this module asks Gemini to generate scenario-based multiple-choice questions
with correct answer keys. The generated questions are stored in the DB and
graded by the same answer-key engine as the static bank — so grading is still
Rp0 per attempt.

Flow:
  1. `start_quiz()` discovers < QUESTIONS_PER_QUIZ questions for the skill.
  2. It calls `ensure_questions_exist(skill)` from this module.
  3. This module calls Gemini once to generate 6 questions + answer keys.
  4. Questions are inserted with `reviewed=False` (marked as AI-generated).
  5. They are NOT served yet — an admin reviews them at `GET /admin/questions`
     first, then they go live for everyone holding that skill. Serving an
     unreviewed question would mean a mis-keyed answer key silently marking
     correct answers wrong, no two candidates answering a comparable quiz, and
     a candidate being able to invent a skill name to summon a fresh, unvetted
     quiz of their own.

The generation cost (~Rp60–130) is paid once per skill and amortised across
all future attempts.  Admin can review/deactivate questions at
`GET /admin/questions`.
"""

from __future__ import annotations

import json
import logging

from backend.app.db import postgres_store as store
from backend.app.db.schemas_proof import SkillQuestion
from backend.app.services.llm_factory import LLMBusyError, build_chat_llm
from backend.app.services.matching.evidence import skill_key

_logger = logging.getLogger(__name__)

GENERATE_COUNT = 6  # questions per skill (quiz draws 5)

_SYSTEM_PROMPT = """\
Kamu adalah pembuat soal kuis skill profesional untuk platform kerja Indonesia.
Buat soal skenario dunia nyata yang menguji kemampuan praktis, bukan hafalan.
Setiap soal punya 4 pilihan (A-D), persis 1 jawaban benar.
Gunakan Bahasa Indonesia.
"""

_USER_PROMPT_TEMPLATE = """\
Buatkan {count} soal kuis skenario untuk skill "{skill_label}".

Aturan:
- Soal harus berbasis skenario kerja nyata, bukan definisi/teori
- 4 pilihan jawaban (A–D), persis 1 jawaban benar
- Bahasa Indonesia, konteks pekerjaan di Indonesia
- Variasikan tingkat kesulitan (2 mudah, 2 sedang, 2 agak sulit)
- Jangan gunakan soal yang terlalu umum/generik

Balas HANYA dengan JSON array, tanpa markdown fence, tanpa penjelasan:
[
  {{
    "question": "...",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "correct_index": 0
  }}
]

correct_index: 0=A, 1=B, 2=C, 3=D.
"""


class GenerationError(Exception):
    """Raised when AI question generation fails."""


async def generate_questions(skill_name: str) -> list[SkillQuestion]:
    """Call Gemini to generate quiz questions for a skill.

    Returns a list of SkillQuestion objects ready to be upserted.
    Raises GenerationError if the LLM call or parsing fails.
    """
    key = skill_key(skill_name)
    label = skill_name.strip()

    prompt = _USER_PROMPT_TEMPLATE.format(count=GENERATE_COUNT, skill_label=label)

    try:
        llm = build_chat_llm(temperature=0.4, task="quiz_generation")
        from langchain_core.messages import HumanMessage, SystemMessage

        result = await llm.ainvoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
    except LLMBusyError:
        raise GenerationError("AI sedang sibuk, coba lagi nanti.")
    except RuntimeError as exc:
        raise GenerationError(f"AI tidak tersedia: {exc}")

    raw = result.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        raw = "\n".join(lines)

    try:
        items = json.loads(raw)
    except json.JSONDecodeError as exc:
        _logger.warning("Quiz generation JSON parse failed for '%s': %s\nRaw: %s", key, exc, raw[:500])
        raise GenerationError("AI mengembalikan format yang tidak valid.") from exc

    if not isinstance(items, list) or len(items) < 1:
        raise GenerationError("AI tidak menghasilkan soal yang cukup.")

    questions: list[SkillQuestion] = []
    for item in items[:GENERATE_COUNT]:
        if not isinstance(item, dict):
            continue
        q_text = item.get("question", "").strip()
        options = item.get("options", [])
        correct = item.get("correct_index", 0)
        if not q_text or len(options) < 4 or not isinstance(correct, int) or correct < 0 or correct >= len(options):
            continue
        # Clean option prefixes like "A. ", "B. " that the LLM may add
        cleaned_options = []
        for opt in options[:4]:
            opt = str(opt).strip()
            if len(opt) > 3 and opt[0] in "ABCD" and opt[1] in ".:)" and opt[2] == " ":
                opt = opt[3:]
            cleaned_options.append(opt)

        questions.append(SkillQuestion(
            skill=key,
            skill_label=label,
            question=q_text,
            options=cleaned_options,
            correct_index=correct,
            reviewed=False,
            active=True,
        ))

    if len(questions) < 5:
        raise GenerationError(
            f"AI hanya menghasilkan {len(questions)} soal valid (butuh minimal 5)."
        )

    _logger.info("Generated %d quiz questions for skill '%s'", len(questions), key)
    return questions


async def ensure_questions_exist(skill_name: str, min_count: int = 5) -> bool:
    """If the skill has fewer than `min_count` active questions, generate them.

    Returns True if new questions were generated and stored, False if enough
    already existed.  Raises GenerationError on failure.
    """
    key = skill_key(skill_name)
    # Counts unreviewed rows too. Generated questions land as reviewed=False, so
    # a reviewed-only check could never see them and this would regenerate (and
    # re-bill) on every call while never becoming serveable.
    if await store.count_questions_for_skill(key) >= min_count:
        return False

    questions = await generate_questions(skill_name)
    repos = store.get_repositories()
    for q in questions:
        await repos.skill_questions.upsert(q)

    return True

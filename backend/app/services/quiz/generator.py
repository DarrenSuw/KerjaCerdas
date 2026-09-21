"""AI quiz question generator — fills each skill's bank toward BANK_TARGET.

Why the bank has to be big
--------------------------
A quiz draws QUESTIONS_PER_QUIZ (5) questions and a failed attempt may be
retaken after RETAKE_DAYS (1). With the old 6-question bank a retake repeated
at least 4 of the 5 questions, so the badge could be obtained by memorising six
items overnight — and the badge feeds a 0.85 proof weight. The cooldown was
never the defence; bank size is. `service._pick_questions` guarantees that
consecutive attempts share no question, which is only satisfiable at all when
the bank holds at least 2x the quiz length, and only unpredictable when it
holds considerably more. Hence BANK_TARGET = 30.

Who may serve a generated question
----------------------------------
Generated items are put through `validate_question()`, a mechanical check with
no AI in it. An item that passes every check becomes servable immediately and
is tagged `source="ai_auto"`; an item that fails any check is stored inactive
as `source="ai_draft"` for a human to fix or discard.

This is a deliberate narrowing of the earlier rule ("no question is served
until a human reviews it"). That rule was correct about the risk but produced a
bank of 8 skills, because review is a human bottleneck and every other skill
simply 404ed. The risks it was protecting against are the ones the validator
now checks mechanically and consistently: a malformed item, a missing or
out-of-range key, duplicate options, or an answer that gives itself away.

What the validator cannot check is whether the *intended* answer is actually
the correct one in the real world. That residual risk is why `source` is
recorded per question and surfaced in the admin queue, why a quiz badge is
worth 0.85 rather than 1.00, and why HR confirmation remains the only full
proof. Never describe an `ai_auto` question as practitioner-reviewed.

Cost: generation is ~Rp85-130 per batch, paid once per skill and amortised over
every future attempt. Grading stays Rp0 — the answer key is local.
"""

from __future__ import annotations

import json
import logging

from backend.app.db import postgres_store as store
from backend.app.db.schemas_proof import SkillQuestion
from backend.app.services.llm_factory import LLMBusyError, build_chat_llm
from backend.app.services.matching.evidence import skill_key

_logger = logging.getLogger(__name__)

# Target size of a healthy bank. With QUESTIONS_PER_QUIZ=5, a 50-question pool
# gives C(50,5)=2,118,760 possible draws — the probability of drawing the exact
# same 5 two days in a row is <0.0005%. This is the primary retake defence.
# BANK_MINIMUM (2x quiz length) is the floor below which two consecutive attempts
# cannot be non-overlapping at all.
BANK_TARGET = 50
BANK_MINIMUM = 10
GENERATE_BATCH = 10  # questions asked for per LLM call
MAX_BATCHES = 6  # hard stop; raised from 4 to fill the larger target

# Options that make a multiple-choice item untestable.
_BANNED_OPTION_PATTERNS = (
    "semua benar",
    "semua salah",
    "tidak ada yang benar",
    "semua jawaban",
    "a dan b",
    "b dan c",
)

_SYSTEM_PROMPT = """\
Kamu adalah pembuat soal kuis skill profesional untuk platform kerja Indonesia.
Buat soal skenario dunia nyata yang menguji kemampuan praktis, bukan hafalan.
Setiap soal punya 4 pilihan (A-D), persis 1 jawaban benar.
Gunakan Bahasa Indonesia.
"""

_USER_PROMPT_TEMPLATE = """\
Buatkan {count} soal kuis skenario untuk skill "{skill_label}".

Aturan:
- Soal berbasis skenario kerja nyata, bukan definisi/teori
- 4 pilihan jawaban (A-D), persis 1 jawaban benar
- Bahasa Indonesia, konteks pekerjaan di Indonesia
- Variasikan tingkat kesulitan
- Panjang keempat pilihan harus mirip — jangan membuat jawaban benar jauh lebih
  panjang atau jauh lebih rinci dari pengecoh, karena itu membocorkan kunci
- Dilarang memakai pilihan "semua benar", "semua salah", atau "A dan B"
- Jangan mengulang soal yang sudah ada di daftar berikut:
{existing}

Balas HANYA dengan JSON array, tanpa markdown fence, tanpa penjelasan:
[
  {{
    "question": "...",
    "options": ["...", "...", "...", "..."],
    "correct_index": 0
  }}
]

correct_index: 0=A, 1=B, 2=C, 3=D.
"""


class GenerationError(Exception):
    """Raised when AI question generation fails."""


def validate_question(q_text: str, options: list[str], correct: int) -> str | None:
    """Return None when the item is servable, else a short reason it is not.

    Mechanical only — no AI, no network. Every rule here exists because it is a
    failure we can detect without knowing the subject matter.
    """
    text = (q_text or "").strip()
    if not 20 <= len(text) <= 400:
        return "panjang pertanyaan di luar 20-400 karakter"
    if len(options) != 4:
        return f"{len(options)} pilihan, harus 4"

    cleaned = [str(o).strip() for o in options]
    if any(not o for o in cleaned):
        return "ada pilihan kosong"
    if any(len(o) > 200 for o in cleaned):
        return "ada pilihan lebih dari 200 karakter"
    if len({o.casefold() for o in cleaned}) != 4:
        return "ada pilihan yang duplikat"
    if not isinstance(correct, int) or not 0 <= correct < 4:
        return "correct_index di luar jangkauan"

    lowered = [o.casefold() for o in cleaned]
    if any(pat in o for o in lowered for pat in _BANNED_OPTION_PATTERNS):
        return "memakai pilihan gabungan / 'semua benar'"

    # A correct answer that is far longer than every distractor is guessable
    # without knowing the subject — the single most common giveaway in
    # AI-written multiple choice.
    answer_len = len(cleaned[correct])
    longest_distractor = max(len(o) for i, o in enumerate(cleaned) if i != correct)
    if answer_len > 2 * longest_distractor:
        return "jawaban benar jauh lebih panjang dari pengecoh"

    # The stem must not contain the answer verbatim.
    if len(cleaned[correct]) >= 12 and cleaned[correct].casefold() in text.casefold():
        return "jawaban benar tersalin di dalam pertanyaan"

    return None


def _strip_option_label(opt: str) -> str:
    opt = str(opt).strip()
    if len(opt) > 3 and opt[0] in "ABCD" and opt[1] in ".:)" and opt[2] == " ":
        return opt[3:].strip()
    return opt


async def generate_questions(
    skill_name: str, count: int = GENERATE_BATCH, existing: list[str] | None = None
) -> list[SkillQuestion]:
    """Ask the model for `count` questions and return the ones worth storing.

    Items that pass `validate_question` come back servable (`reviewed=True`,
    `source="ai_auto"`); items that fail come back inactive as `"ai_draft"` so a
    human can repair them instead of the work being silently thrown away.
    """
    key = skill_key(skill_name)
    label = skill_name.strip()
    seen = "\n".join(f"- {q[:120]}" for q in (existing or [])[:40]) or "- (belum ada)"
    prompt = _USER_PROMPT_TEMPLATE.format(count=count, skill_label=label, existing=seen)

    try:
        llm = build_chat_llm(temperature=0.6, task="quiz_generation")
        from langchain_core.messages import HumanMessage, SystemMessage

        result = await llm.ainvoke(
            [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=prompt)]
        )
    except LLMBusyError:
        raise GenerationError("AI sedang sibuk, coba lagi nanti.") from None
    except RuntimeError as exc:
        raise GenerationError(f"AI tidak tersedia: {exc}") from exc

    raw = result.content.strip()
    if raw.startswith("```"):
        raw = "\n".join(ln for ln in raw.split("\n") if not ln.strip().startswith("```"))

    try:
        items = json.loads(raw)
    except json.JSONDecodeError as exc:
        _logger.warning("Quiz generation JSON parse failed for '%s': %s", key, exc)
        raise GenerationError("AI mengembalikan format yang tidak valid.") from exc

    if not isinstance(items, list) or not items:
        raise GenerationError("AI tidak menghasilkan soal yang cukup.")

    existing_texts = {t.strip().casefold() for t in (existing or [])}
    out: list[SkillQuestion] = []
    for item in items[:count]:
        if not isinstance(item, dict):
            continue
        q_text = str(item.get("question", "")).strip()
        options = [_strip_option_label(o) for o in item.get("options", [])][:4]
        correct = item.get("correct_index", 0)

        # A repeat of something already banked is worse than useless: it would
        # count toward the target while shrinking the pool of distinct items
        # that `_pick_questions` can draw a non-overlapping retake from.
        if q_text.casefold() in existing_texts:
            continue
        existing_texts.add(q_text.casefold())

        problem = validate_question(q_text, options, correct)
        out.append(
            SkillQuestion(
                skill=key,
                skill_label=label,
                question=q_text,
                options=options,
                correct_index=correct if isinstance(correct, int) and 0 <= correct < 4 else 0,
                reviewed=problem is None,
                active=problem is None,
                source="ai_draft" if problem else "ai_auto",
                review_note=problem or "",
            )
        )

    if not any(q.active for q in out):
        raise GenerationError("Tidak ada soal hasil AI yang lolos pemeriksaan bentuk.")
    return out


async def ensure_questions_exist(skill_name: str, target: int = BANK_TARGET) -> int:
    """Top the skill's bank up toward `target`. Returns how many became servable.

    Safe to call on every quiz start: it counts first and returns 0 without any
    AI call once the bank is full. Batches are capped by MAX_BATCHES so a skill
    that the model keeps failing on cannot bill indefinitely.
    """
    key = skill_key(skill_name)
    repos = store.get_repositories()
    added = 0

    for _ in range(MAX_BATCHES):
        have = await store.count_active_questions_for_skill(key)
        if have >= target:
            break
        existing = [q.question for q in await store.find_active_questions(key)]
        batch = await generate_questions(
            skill_name, count=min(GENERATE_BATCH, target - have), existing=existing
        )
        for q in batch:
            await repos.skill_questions.upsert(q)
            if q.active:
                added += 1
        # Stop the moment a batch stops making progress. A model that keeps
        # returning duplicates or items the validator rejects would otherwise
        # bill MAX_BATCHES calls on every single quiz start for a skill that
        # can never reach the target.
        if await store.count_active_questions_for_skill(key) <= have:
            break

    if added:
        _logger.info("Bank '%s': +%d servable questions", key, added)
    return added

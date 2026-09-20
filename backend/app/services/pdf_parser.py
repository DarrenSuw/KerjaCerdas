"""PDF → structured JSON via Gemini multimodal.

Two entry points:
  • parse_cv(pdf_bytes)        → dict matching tasks/cv_parser.md schema
  • parse_job_pack(pdf_bytes)  → dict matching tasks/job_parser.md schema

Both go through `gemini_chat` so every call is logged for admin review.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.app.api.middleware.sanitization import clean_extracted_text
from backend.app.config.settings import settings
from backend.app.services.privacy.redact import redact_text
from backend.app.services.prompt_loader import build_system_prompt

logger = logging.getLogger(__name__)


class _NoKey(RuntimeError):
    pass


_MAX_GEMINI_PAGES = 3


def _cap_pdf_pages(pdf_bytes: bytes, max_pages: int = _MAX_GEMINI_PAGES) -> bytes:
    """Truncate a PDF to its first `max_pages` pages before it is billed per-page by Gemini.

    Gemini's multimodal endpoint bills PDFs per page, so a legitimate-looking
    but very long upload costs proportionally more per parse with no cap in
    place. Raises if the PDF can't be parsed here — callers must not fall
    through to sending the original, potentially much longer, document to
    Gemini uncapped, which would defeat the entire point of the cap.
    """
    import fitz  # PyMuPDF

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        if doc.page_count <= max_pages:
            return pdf_bytes
        doc.select(range(max_pages))
        return doc.tobytes()


def _client():
    """Return a google-genai client — Vertex AI if a project is set, else AI Studio."""
    import os

    from google import genai

    project = (
        settings.vertex_ai_project
        or os.environ.get("VERTEX_AI_PROJECT", "")
        or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    )
    if project:
        location = settings.vertex_ai_location or os.environ.get(
            "VERTEX_AI_LOCATION", "us-central1"
        )
        return genai.Client(vertexai=True, project=project, location=location)
    key = (
        settings.gemini_api_key
        or os.environ.get("GEMINI_API_KEY", "")
        or os.environ.get("GOOGLE_API_KEY", "")
    )
    if not key:
        raise _NoKey("Neither GEMINI_API_KEY nor VERTEX_AI_PROJECT configured")
    return genai.Client(api_key=key)


def _pdf_to_text(pdf_bytes: bytes, max_chars: int = 8000) -> str:
    """Cheap text extraction so we always have *some* signal even offline.

    Uses PyMuPDF (fitz) for reliable text extraction.
    """
    try:
        import fitz  # PyMuPDF

        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            out: list[str] = []
            for page in doc:
                out.append(page.get_text())
                if sum(len(s) for s in out) > max_chars:
                    break
            text = "\n".join(out).strip()
            return text[:max_chars]
    except Exception as e:
        logger.warning("PyMuPDF fallback extraction failed: %s", e)
        return ""


_SKILL_VOCAB = {
    # programming
    "python",
    "java",
    "javascript",
    "typescript",
    "go",
    "golang",
    "rust",
    "c++",
    "c#",
    "php",
    "ruby",
    "kotlin",
    "swift",
    "scala",
    "r",
    # web/fe
    "react",
    "next.js",
    "nextjs",
    "vue",
    "angular",
    "svelte",
    "tailwind",
    "node",
    "nodejs",
    # backend / infra
    "fastapi",
    "django",
    "flask",
    "spring",
    "spring boot",
    "express",
    "graphql",
    "grpc",
    "rest",
    "microservices",
    "kafka",
    "rabbitmq",
    "redis",
    "elasticsearch",
    # cloud
    "aws",
    "gcp",
    "azure",
    "docker",
    "kubernetes",
    "k8s",
    "terraform",
    "ansible",
    # data
    "postgresql",
    "postgres",
    "mysql",
    "mongodb",
    "bigquery",
    "snowflake",
    "spark",
    "pandas",
    "numpy",
    "scikit-learn",
    "tensorflow",
    "pytorch",
    "langchain",
    "langgraph",
    # design / pm
    "figma",
    "sketch",
    "jira",
    "scrum",
    "agile",
    "product management",
}


def _fallback_extract(pdf_bytes: bytes) -> dict[str, Any]:
    """Best-effort heuristic extraction when no AI key is available.

    Pulls plain text from the PDF and tries to recognise full name, headline,
    skills (against a small vocabulary), and education year. Guaranteed to
    return a schema-shaped dict so downstream code never breaks.
    """
    text = _pdf_to_text(pdf_bytes)
    if not text:
        return _offline_stub("cv_parser")

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # Heuristic: name is the first non-empty line that's not an email/phone
    name = next(
        (
            ln
            for ln in lines[:6]
            if "@" not in ln and not re.search(r"\d{4,}", ln) and 2 <= len(ln.split()) <= 6
        ),
        "Pengguna",
    )
    headline = next(
        (
            ln
            for ln in lines[1:8]
            if 4 <= len(ln) <= 80 and not re.search(r"\d{4}", ln) and ln != name
        ),
        "",
    )

    text_low = text.lower()
    skills = sorted({s for s in _SKILL_VOCAB if s in text_low})
    # Education year — last 4-digit year in the doc that's a plausible grad year
    years = [int(y) for y in re.findall(r"(19[89]\d|20[0-3]\d)", text)]
    grad_year = max(years) if years else 0
    degree = (
        "S2"
        if "magister" in text_low or "master" in text_low
        else "S1"
        if "sarjana" in text_low or "bachelor" in text_low or "s1 " in text_low
        else "D3"
        if "diploma" in text_low
        else "S1"
    )

    # Strip PII from resume_text for storage
    from backend.app.services.privacy.redact import redact_text

    redacted = redact_text(text)

    return {
        "full_name": name,
        "headline": headline or "Profesional",
        "region_code": "3171" if "jakarta" in text_low else "",
        "skills": [{"name": s, "level": "intermediate", "years": 0} for s in skills[:25]],
        "experience": [],
        "education": [
            {"institution": "", "degree": degree, "major": "", "graduation_year": grad_year or 2024}
        ],
        "salary_expectation_min": 0,
        "salary_expectation_max": 0,
        "resume_text": redacted[:1000],
        "_offline": True,
        "_extraction_mode": "text_heuristic",
    }


def _extract_json(text: str) -> dict[str, Any]:
    """Be lenient about ```json fences."""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    blob = m.group(1) if m else text
    return json.loads(blob)


_MIN_TEXT_FOR_REDACTED_PATH = 200


class ScannedPdfError(Exception):
    """Raised when a PDF has no text layer, so its contents cannot be redacted.

    Deliberately not a soft fallback: we would rather refuse the upload and ask
    for manual entry than send an un-redactable image of someone's CV to a
    third-party model.
    """


def _llm_contents(
    types, pdf_bytes: bytes, allow_scanned: bool = False, _text_override: str | None = None
) -> list:
    """What is actually sent to Gemini for a PDF.

    Normal case: the PDF is converted to text locally and PII-redacted (email /
    phone / NIK) before anything leaves the server.

    Scanned or photographed CVs have no text layer, so there is nothing to run
    the regex over and the document can only be sent as an image — carrying the
    same contact details the regex exists to strip. We do NOT silently do that:
    the first call raises ScannedPdfError, the API turns that into a consent
    prompt, and only an explicit `confirm_scanned` re-upload passes
    allow_scanned=True.

    Refusing outright was the first implementation and it was wrong for this
    market: a scan or a phone photo is how a great many Indonesian job seekers
    actually hold their CV, and blocking them would exclude exactly the people
    this product exists for. Informed consent is the honest trade, and it is
    also the UU PDP posture where explicit consent is the lawful basis.
    Whatever the model returns is still redacted before it is stored.

    `_text_override` exists only so tests can drive both branches without
    building real scanned and text-layer PDFs.
    """
    from backend.app.services.privacy.redact import redact_text

    instruction = "Ekstrak data terstruktur sesuai schema di task prompt. Kembalikan JSON saja."
    if _text_override is not None:
        text = _text_override
    else:
        try:
            text = _pdf_to_text(pdf_bytes, max_chars=20000)
        except Exception:  # noqa: BLE001 — treated the same as an empty text layer
            text = ""
    if len(text.strip()) < _MIN_TEXT_FOR_REDACTED_PATH:
        if not allow_scanned:
            raise ScannedPdfError(
                "CV ini berupa hasil pindai atau foto, jadi tidak ada teks yang bisa kami "
                "samarkan lebih dulu. Untuk membacanya, gambar dokumen perlu dikirim ke AI "
                "apa adanya — termasuk nomor HP dan email yang tertulis di dalamnya. "
                "Hasil bacaannya tetap kami samarkan sebelum disimpan."
            )
        return [types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"), instruction]
    header = "Isi dokumen (data kontak sudah disamarkan):"
    return [f"{header}\n\n{redact_text(text)}", instruction]


async def _call_gemini(
    pdf_bytes: bytes, role: str, task: str, allow_scanned: bool = False
) -> dict[str, Any]:
    import asyncio

    try:
        client = _client()
    except _NoKey:
        logger.warning("Gemini auth missing — using text-heuristic fallback for task=%s", task)
        if task == "cv_parser":
            return await asyncio.to_thread(_fallback_extract, pdf_bytes)
        return _offline_stub(task)

    system = build_system_prompt(role=role, task=task)

    def _sync():
        from google.genai import types

        from backend.app.services.llm_factory import chat_model_chain

        last_exc: Exception | None = None
        for model in chat_model_chain():
            try:
                resp = client.models.generate_content(
                    model=model,
                    contents=_llm_contents(types, pdf_bytes, allow_scanned=allow_scanned),
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        response_mime_type="application/json",
                        temperature=settings.parser_temperature,
                        http_options=types.HttpOptions(
                            timeout=30_000,  # ms — cap each model attempt
                            retry_options=types.HttpRetryOptions(attempts=1),
                        ),
                    ),
                )
                usage = getattr(resp, "usage_metadata", None)
                _last_usage.update(
                    model=model,
                    tokens_in=int(getattr(usage, "prompt_token_count", 0) or 0),
                    tokens_out=int(getattr(usage, "candidates_token_count", 0) or 0),
                )
                return resp.text or "{}"
            except Exception as exc:  # 429/quota → try next model in the chain
                logger.warning("Gemini PDF call failed on %s (%s) — trying next model", model, exc)
                last_exc = exc
        raise last_exc if last_exc else RuntimeError("no chat models configured")

    _last_usage: dict = {}
    try:
        import time as _time

        from backend.app.db.postgres_store import record_ai_usage

        pdf_bytes = await asyncio.to_thread(_cap_pdf_pages, pdf_bytes)
        _t0 = _time.monotonic()
        raw = await asyncio.to_thread(_sync)
        await record_ai_usage(
            task,
            _last_usage.get("model", ""),
            _last_usage.get("tokens_in", 0),
            _last_usage.get("tokens_out", 0),
            int((_time.monotonic() - _t0) * 1000),
        )
    except Exception as e:  # network/SSL/quota/parsing/page-cap — never crash the upload
        logger.warning("Gemini PDF call failed (task=%s): %s — falling back", task, e)
        if task == "cv_parser":
            fb = await asyncio.to_thread(_fallback_extract, pdf_bytes)
            fb["_offline_reason"] = str(e)[:200]
            return fb
        stub = _offline_stub(task)
        stub["_offline_reason"] = str(e)[:200]
        return stub

    try:
        raw_dict = _extract_json(raw)
        return (
            _validate_cv_schema(raw_dict)
            if task == "cv_parser"
            else _validate_job_pack_schema(raw_dict)
        )
    except Exception as e:
        logger.error("Gemini returned non-JSON (task=%s): %s", task, e)
        if task == "cv_parser":
            return await asyncio.to_thread(_fallback_extract, pdf_bytes)
        return _offline_stub(task)


_SKILL_LEVELS = {"beginner", "intermediate", "advanced", "expert"}


def _normalize_skill_level(raw: Any) -> str:
    level = str(raw or "").strip().lower()
    return level if level in _SKILL_LEVELS else "intermediate"


def _validate_cv_schema(d: dict[str, Any]) -> dict[str, Any]:
    """Coerce Gemini output to the strict, sanitized schema uploads.py expects."""
    return {
        "full_name": clean_extracted_text(str(d.get("full_name") or "Pengguna"), max_length=100),
        "headline": clean_extracted_text(str(d.get("headline") or ""), max_length=200),
        "region_code": clean_extracted_text(str(d.get("region_code") or ""), max_length=10),
        "skills": [
            {
                "name": clean_extracted_text(str(s.get("name", "")), max_length=60),
                "level": _normalize_skill_level(s.get("level")),
                "years": float(s.get("years") or 0),
            }
            for s in (d.get("skills") or [])
            if isinstance(s, dict) and s.get("name")
        ],
        "experience": [
            {
                "company": clean_extracted_text(str(x.get("company", "")), max_length=150),
                "title": clean_extracted_text(str(x.get("title", "")), max_length=150),
                "start_date": str(x.get("start_date") or "2024-01"),
                "end_date": (str(x["end_date"]) if x.get("end_date") is not None else None),
                "description": clean_extracted_text(str(x.get("description", "")), max_length=1000),
            }
            for x in (d.get("experience") or [])
            if isinstance(x, dict)
        ],
        "education": [
            {
                "institution": clean_extracted_text(str(e.get("institution", "")), max_length=150),
                "degree": (e.get("degree") or "S1").upper(),
                "major": clean_extracted_text(str(e.get("major", "")), max_length=100),
                "graduation_year": int(e.get("graduation_year") or 2024),
            }
            for e in (d.get("education") or [])
            if isinstance(e, dict)
        ],
        "salary_expectation_min": int(d.get("salary_expectation_min") or 0),
        "salary_expectation_max": int(d.get("salary_expectation_max") or 0),
        # Redacted, not merely cleaned. Whatever Gemini echoes back can still
        # contain the phone/email/NIK it read off the CV, and this stored value
        # is fed verbatim to the embedding API by matcher._build_seeker_text —
        # a path that never passes through llm_factory's redact_llm_input.
        "resume_text": redact_text(
            clean_extracted_text(str(d.get("resume_text") or ""), max_length=2000)
        ),
    }


def _validate_job_pack_schema(d: dict[str, Any]) -> dict[str, Any]:
    """Coerce Gemini job pack output to a clean, sanitized posting list."""
    postings_raw = d.get("postings") or []
    cleaned_postings: list[dict[str, Any]] = []

    for p in postings_raw:
        if not isinstance(p, dict):
            continue
        cleaned_postings.append(
            {
                "title": clean_extracted_text(str(p.get("title") or "Untitled"), max_length=150),
                "description": clean_extracted_text(
                    str(p.get("description") or ""), max_length=3000
                ),
                "responsibilities": [
                    clean_extracted_text(str(r), max_length=300)
                    for r in (p.get("responsibilities") or [])
                    if isinstance(r, (str, int, float)) and str(r).strip()
                ],
                "required_skills": [
                    clean_extracted_text(str(s), max_length=60)
                    for s in (p.get("required_skills") or [])
                    if isinstance(s, (str, int, float)) and str(s).strip()
                ],
                "nice_to_have_skills": [
                    clean_extracted_text(str(s), max_length=60)
                    for s in (p.get("nice_to_have_skills") or [])
                    if isinstance(s, (str, int, float)) and str(s).strip()
                ],
                "education_min": (p.get("education_min") or "SMA").upper(),
                "experience_years_min": int(p.get("experience_years_min") or 0),
                "region_code": clean_extracted_text(str(p.get("region_code") or ""), max_length=10),
                "remote_allowed": bool(p.get("remote_allowed", False)),
                "salary_min": int(p.get("salary_min") or 0),
                "salary_max": int(p.get("salary_max") or 0),
                "kbji_code": clean_extracted_text(str(p.get("kbji_code") or ""), max_length=20),
            }
        )

    return {"postings": cleaned_postings}


async def parse_cv(pdf_bytes: bytes, allow_scanned: bool = False) -> dict[str, Any]:
    """Parse a CV. `allow_scanned` is the seeker's explicit consent to send an
    un-redactable scan/photo as an image — see _llm_contents."""
    return await _call_gemini(
        pdf_bytes, role="seeker_advisor", task="cv_parser", allow_scanned=allow_scanned
    )


async def parse_job_pack(pdf_bytes: bytes) -> dict[str, Any]:
    return await _call_gemini(pdf_bytes, role="employer_analyst", task="job_parser")


# ── Offline stubs so dev mode (no key) still produces something usable ────────


def _offline_stub(task: str) -> dict[str, Any]:
    if task == "cv_parser":
        return {
            "full_name": "Pengguna Demo",
            "headline": "Lulusan baru, siap belajar",
            "region_code": "3171",
            "skills": [
                {"name": "Python", "level": "intermediate", "years": 1},
                {"name": "SQL", "level": "beginner", "years": 0.5},
            ],
            "experience": [],
            "education": [
                {
                    "institution": "Universitas Demo",
                    "degree": "S1",
                    "major": "Teknik Informatika",
                    "graduation_year": 2024,
                }
            ],
            "salary_expectation_min": 5_000_000,
            "salary_expectation_max": 9_000_000,
            "resume_text": "[offline-stub] aktifkan GEMINI_API_KEY untuk parsing PDF asli.",
            "_offline": True,
        }
    if task == "job_parser":
        return {
            "postings": [
                {
                    "title": "Junior Software Engineer",
                    "description": "[offline-stub] posting demo.",
                    "responsibilities": ["Develop features", "Write tests"],
                    "required_skills": ["Python", "Git"],
                    "nice_to_have_skills": ["Docker"],
                    "education_min": "SMA",
                    "experience_years_min": 0,
                    "region_code": "3171",
                    "remote_allowed": True,
                    "salary_min": 7_000_000,
                    "salary_max": 12_000_000,
                    "kbji_code": "",
                    "_offline": True,
                }
            ]
        }
    return {}

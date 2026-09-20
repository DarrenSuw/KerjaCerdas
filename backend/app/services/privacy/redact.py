"""Deterministic PII redaction applied BEFORE any text reaches an LLM.

Prompt instructions ("do not repeat personal data") can fail, so they are only
a second layer. This module removes contact data with fixed rules first:

  email addresses        -> [email]
  16-digit NIK numbers   -> [nik]
  phone numbers          -> [phone]

Used by llm_factory (every chat call) and pdf_parser (CV text is extracted
and redacted locally before being sent for structured extraction).
"""

from __future__ import annotations

import re
from typing import Any

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_NIK = re.compile(r"\b\d{16}\b")
# +62 / 0 prefixed Indonesian numbers and generic 8+ digit sequences with
# separators. Checked after NIK so a 16-digit NIK is labelled as such.
_PHONE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)")


def redact_text(text: str) -> str:
    if not text:
        return text
    out = _EMAIL.sub("[email]", text)
    out = _NIK.sub("[nik]", out)
    out = _PHONE.sub("[phone]", out)
    return out


def _redact_content(content: Any) -> Any:
    if isinstance(content, str):
        return redact_text(content)
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(redact_text(part))
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append({**part, "text": redact_text(part["text"])})
            else:
                parts.append(part)
        return parts
    return content


def redact_llm_input(value: Any) -> Any:
    """Redact a LangChain invoke() input: a string, a message, or a list of messages."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_llm_input(v) for v in value]
    content = getattr(value, "content", None)
    if content is not None and hasattr(value, "model_copy"):
        return value.model_copy(update={"content": _redact_content(content)})
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[1], str):
        return (value[0], redact_text(value[1]))
    return value

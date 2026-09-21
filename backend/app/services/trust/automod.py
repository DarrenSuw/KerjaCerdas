"""AutoMod for job postings — checked before a job goes live.

Layer 1 (always): fixed rules, deterministic and explainable.
Layer 2 (only when a Gemini key is configured): an AI scam-pattern check that
can only *hold* a job for a human, never reject it on its own.

Outcomes:
  published  no rule hit
  held       waiting for admin review (soft rule hit, AI flag, or first-job review)
  rejected   hard rule hit (asking candidates for money) — the poster gets a
             notice with the exact sentence and how to fix it, and can edit &
             resubmit or appeal.

Every reason carries {rule, severity, excerpt, fix} so the poster notice can
quote the flagged sentence (Discord-AutoMod style).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# (rule id, severity, pattern, fix text)
_RULES: list[tuple[str, str, re.Pattern[str], str]] = [
    (
        "fee_to_candidate",
        "hard",
        re.compile(
            r"(biaya|bayar|transfer|deposit|uang jaminan|dp)\s*(\w+\s){0,4}"
            r"(pelatihan|training|seragam|administrasi|pendaftaran|medical|mcu|tiket|jaminan)",
            re.I,
        ),
        "Lowongan tidak boleh meminta pelamar membayar apa pun. Hapus kalimat tentang biaya.",
    ),
    (
        "age_limit",
        "soft",
        re.compile(r"(usia|umur)\s*(maks(imal)?|max|tidak lebih dari|di ?bawah)\s*\d{2}", re.I),
        "Batas usia termasuk diskriminatif kecuali diwajibkan aturan. Hapus atau jelaskan alasannya.",
    ),
    (
        "appearance",
        "soft",
        re.compile(r"(berpenampilan menarik|good looking|cantik|tampan|tinggi badan min)", re.I),
        "Syarat penampilan fisik termasuk diskriminatif. Ganti dengan syarat kemampuan kerja.",
    ),
    (
        "gender_only",
        "soft",
        re.compile(r"\b(khusus|hanya)\s+(pria|wanita|laki-laki|perempuan)\b", re.I),
        "Syarat jenis kelamin hanya boleh bila ada alasan pekerjaan yang jelas. Jelaskan atau hapus.",
    ),
    (
        "offplatform_contact",
        "soft",
        re.compile(r"(hubungi|chat|kirim cv)\s*(\w+\s){0,3}(telegram|t\.me/)", re.I),
        "Hindari meminta pelamar menghubungi lewat Telegram. Gunakan tombol Lamar di KerjaCerdas.",
    ),
]

# Salary sanity bounds (IDR per month). Far outside the BPS Feb 2026 average
# wage (Rp3.29M) in either direction is a common scam / typo signal.
_SALARY_TOO_HIGH = 100_000_000
_SALARY_TOO_LOW = 300_000


@dataclass
class Verdict:
    decision: str = "published"  # published | held | rejected
    reasons: list[dict] = field(default_factory=list)


def _excerpt(text: str, match: re.Match[str]) -> str:
    start = max(0, match.start() - 40)
    end = min(len(text), match.end() + 40)
    return ("…" if start else "") + text[start:end].strip() + ("…" if end < len(text) else "")


def check_rules(title: str, description: str, responsibilities: list[str],
                salary_min: int = 0, salary_max: int = 0) -> Verdict:
    text = "\n".join([title or "", description or "", *[r for r in responsibilities or [] if r]])
    verdict = Verdict()
    for rule_id, severity, pattern, fix in _RULES:
        m = pattern.search(text)
        if m:
            verdict.reasons.append(
                {"rule": rule_id, "severity": severity, "excerpt": _excerpt(text, m), "fix": fix}
            )
    if salary_max and salary_max > _SALARY_TOO_HIGH or (salary_min and salary_min < _SALARY_TOO_LOW):
        verdict.reasons.append({
            "rule": "salary_outlier", "severity": "soft",
            "excerpt": f"Gaji Rp{salary_min:,} - Rp{salary_max:,}".replace(",", "."),
            "fix": "Periksa kembali angka gaji per bulan.",
        })
    if any(r["severity"] == "hard" for r in verdict.reasons):
        verdict.decision = "rejected"
    elif verdict.reasons:
        verdict.decision = "held"
    return verdict


async def ai_scam_check(title: str, description: str) -> dict | None:
    """Optional second layer. Returns a soft reason when the model flags the ad."""
    from backend.app.services.llm_factory import build_chat_llm, resolve_gemini_key

    if not resolve_gemini_key():
        return None
    try:
        from langchain_core.messages import HumanMessage

        from backend.app.utils import content_to_text

        prompt = (
            "Kamu moderator lowongan kerja di Indonesia. Jawab satu baris saja: "
            "'AMAN' atau 'CURIGA: <alasan singkat>'. Curigai lowongan palsu "
            "(janji gaji tidak wajar tanpa syarat, minta data pribadi berlebih, "
            "minta biaya, perusahaan tidak jelas).\n\n"
            f"Judul: {title}\nDeskripsi: {description[:3000]}"
        )
        resp = await build_chat_llm(temperature=0.0, task="automod").ainvoke([HumanMessage(content=prompt)])
        answer = content_to_text(resp.content).strip()
        if answer.upper().startswith("CURIGA"):
            return {"rule": "ai_scam_signal", "severity": "soft",
                    "excerpt": answer[:200], "fix": "Admin akan meninjau lowongan ini."}
    except Exception as exc:  # noqa: BLE001 — AI layer is best-effort
        logger.warning("AutoMod AI check skipped: %s", exc)
    return None


async def moderate(title: str, description: str, responsibilities: list[str],
                   salary_min: int = 0, salary_max: int = 0) -> Verdict:
    verdict = check_rules(title, description, responsibilities, salary_min, salary_max)
    if verdict.decision == "published":
        flag = await ai_scam_check(title, description)
        if flag:
            verdict.reasons.append(flag)
            verdict.decision = "held"
    return verdict


async def review_reported_posting(
    title: str, description: str, cited_rule_ids: list[str]
) -> dict:
    """Judge a flagged posting against the rules its reporters actually cited.

    This is the only place an AI verdict can hide a live posting, and it is
    deliberately narrow. The model is never asked the open question "is this a
    scam" — it is handed one rule at a time, with the rule's own wording, and
    allowed three answers: LANGGAR, TIDAK, or RAGU. Anything but a clear LANGGAR
    leaves the posting up and sends the case to a human. A moderation system
    whose failure mode is "an uncertain model removed a real employer's advert"
    would cost us the side of the market that is hardest to win back.

    Returns {"verdict": "violation"|"clear"|"uncertain", "rule": id|"", "note": str}.
    """
    from backend.app.services.llm_factory import build_chat_llm, resolve_gemini_key
    from backend.app.services.trust.rules import RULES_BY_ID

    rules = [RULES_BY_ID[r] for r in cited_rule_ids if r in RULES_BY_ID]
    if not rules:
        # Nothing checkable was cited — a human decides, nothing is hidden.
        return {"verdict": "uncertain", "rule": "", "note": "tidak ada aturan yang dikutip"}
    if not resolve_gemini_key():
        return {"verdict": "uncertain", "rule": "", "note": "AI tidak tersedia"}

    try:
        from langchain_core.messages import HumanMessage

        from backend.app.utils import content_to_text

        for rule in rules:
            prompt = (
                "Kamu moderator lowongan kerja di Indonesia. Periksa HANYA apakah "
                "lowongan di bawah melanggar satu aturan berikut. Jangan menilai "
                "hal lain.\n\n"
                f"Aturan {rule.id}: {rule.title}\n{rule.detail}\n\n"
                f"Judul: {title}\nDeskripsi: {description[:3000]}\n\n"
                "Jawab satu baris: 'LANGGAR: <kutipan kalimat yang melanggar>' "
                "bila jelas melanggar, 'TIDAK' bila jelas tidak, atau 'RAGU' "
                "bila tidak yakin. Pilih RAGU kalau perlu konteks di luar teks."
            )
            resp = await build_chat_llm(temperature=0.0, task="automod").ainvoke(
                [HumanMessage(content=prompt)]
            )
            answer = content_to_text(resp.content).strip()
            if answer.upper().startswith("LANGGAR"):
                return {"verdict": "violation", "rule": rule.id, "note": answer[:300]}
            if answer.upper().startswith("RAGU"):
                return {"verdict": "uncertain", "rule": rule.id, "note": answer[:300]}
        return {"verdict": "clear", "rule": "", "note": "tidak ditemukan pelanggaran"}
    except Exception as exc:  # noqa: BLE001 — never let the reviewer break reporting
        logger.warning("Report review skipped: %s", exc)
        return {"verdict": "uncertain", "rule": "", "note": "pemeriksaan gagal"}

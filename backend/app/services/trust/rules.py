"""Published posting rules, reporter weighting, and the community-flag pipeline.

Why this replaces "3 reports and the job disappears"
----------------------------------------------------
The old rule hid a posting as soon as three distinct users reported it, with no
check on whether anything had actually been broken. Three coordinated accounts
could therefore take a competitor's posting down, and a report from a brand-new
unverified account counted exactly as much as one from a candidate who had
applied and been asked for money. It was simultaneously too harsh (instant
removal on an unverified accusation) and too weak (no verdict, so a genuine
scam sat live until a third person happened to report it).

The model here is a moderated community, not a tripwire:

  1. **Rules are published.** RULES below is the same list shown to employers
     before posting, to candidates in the report dialog, and handed to the AI
     reviewer. Nobody is moderated against a standard they cannot read.
  2. **A report must cite a rule.** Free text alone cannot start anything, and
     the AI reviewer is only ever asked "does this posting break THIS rule",
     never the open-ended "is this bad", which is where a model hallucinates.
  3. **Reports are weighted, not counted.** Verified, invested reporters weigh
     more; a reporter whose accusations keep getting dismissed weighs nothing.
  4. **Reaching the threshold flags, it does not remove.** A flagged posting
     stays visible and carries a notice. Only a confirmed violation — by the AI
     reviewer against the cited rule, or by an admin — hides it.
  5. **The AI can only escalate to review, never to removal by itself** for
     anything but a hard rule, and a human can always overturn it.

The same ladder applies to candidates (see `seeker_flag_state`): an employer
reporting a candidate raises a flag, not a ban.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

# Weighted report score at which a posting becomes "perlu ditindak lebih
# lanjut". Tuned so that it needs either two invested, verified reporters or
# three ordinary verified ones — not three throwaway accounts.
FLAG_WEIGHT_THRESHOLD = 5

# A reporter whose reports keep being dismissed stops counting. Not a ban:
# they can still report, the report is still recorded for an admin, it just no
# longer moves the automatic threshold on its own.
DISMISSED_REPORTS_TO_MUTE = 3

MIN_ACCOUNT_AGE_DAYS = 3


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    severity: str  # "hard" -> reject on sight | "soft" -> hold for review
    detail: str
    fix: str


# The public rulebook. Ids are stable and quoted in notices, reports and appeals.
RULES: tuple[Rule, ...] = (
    Rule(
        "R1",
        "Lowongan tidak boleh meminta biaya apa pun dari pelamar",
        "hard",
        "Termasuk biaya pelatihan, seragam, administrasi, medical check-up, "
        "tiket, atau uang jaminan — sebelum maupun sesudah diterima.",
        "Hapus seluruh kalimat yang meminta pelamar membayar.",
    ),
    Rule(
        "R2",
        "Lowongan harus mewakili pekerjaan dan perusahaan yang nyata",
        "soft",
        "Nama perusahaan, lokasi, dan pekerjaannya harus benar-benar ada dan "
        "sesuai dengan yang ditawarkan.",
        "Lengkapi identitas perusahaan, atau ajukan verifikasi 'Ditinjau admin'.",
    ),
    Rule(
        "R3",
        "Syarat tidak boleh diskriminatif",
        "soft",
        "Batas usia, jenis kelamin, atau penampilan fisik hanya boleh bila "
        "memang diwajibkan sifat pekerjaannya, dan alasannya harus ditulis.",
        "Ganti dengan syarat kemampuan kerja, atau jelaskan alasannya.",
    ),
    Rule(
        "R4",
        "Proses lamaran tidak boleh dipindahkan ke kanal pribadi",
        "soft",
        "Meminta pelamar menghubungi Telegram pribadi atau nomor tak dikenal "
        "adalah pola penipuan lowongan yang paling umum.",
        "Gunakan tombol Lamar di KerjaCerdas.",
    ),
    Rule(
        "R5",
        "Gaji dan bentuk kerja harus ditulis jujur",
        "soft",
        "Angka gaji yang jauh di luar kewajaran, atau yang berbeda dari yang "
        "dijanjikan saat wawancara, termasuk pelanggaran.",
        "Tulis rentang gaji yang sebenarnya.",
    ),
    Rule(
        "R6",
        "Dilarang meminta dokumen identitas sensitif di tahap lamaran",
        "soft",
        "KTP, KK, ijazah asli, atau NPWP tidak boleh diminta sebelum tahap "
        "wawancara resmi.",
        "Minta dokumen itu saat wawancara, bukan di iklan.",
    ),
)

RULES_BY_ID = {r.id: r for r in RULES}


def rulebook() -> list[dict]:
    """Serialisable rulebook for the API, the report dialog and the posting form."""
    return [
        {"id": r.id, "title": r.title, "severity": r.severity, "detail": r.detail, "fix": r.fix}
        for r in RULES
    ]


def reporter_weight(
    *,
    email_verified: bool,
    applied_to_job: bool,
    account_age_days: float,
    upheld_reports: int,
    dismissed_reports: int,
) -> int:
    """How much this person's report counts toward the flag threshold.

    The signals are all things an abuser has to spend real effort to fake:
    a verified address, an account with some age, an actual application to the
    posting being reported, and a history of accusations that held up.
    """
    if dismissed_reports >= DISMISSED_REPORTS_TO_MUTE:
        return 0
    if not email_verified or account_age_days < MIN_ACCOUNT_AGE_DAYS:
        # Recorded for an admin, but cannot move the automatic threshold: this
        # is exactly the account a brigade creates.
        return 0

    weight = 2
    if applied_to_job:
        # They went through the process being complained about.
        weight += 1
    if upheld_reports > 0:
        weight += 1
    return weight


def flag_state(weighted_score: int, reports: int) -> str:
    """published -> flagged. Never straight to hidden; only a verdict hides."""
    return "flagged" if weighted_score >= FLAG_WEIGHT_THRESHOLD and reports >= 2 else "published"


def seeker_flag_state(
    *, upheld_against: int, now: datetime | None = None, last_at: datetime | None = None
) -> dict:
    """Candidate-side ladder, mirroring the employer strike ladder.

    Deliberately slower than the employer one: a candidate has far less power to
    cause harm than a posting seen by hundreds, and a wrongly limited candidate
    loses income. Warning, then a cap on how many applications a day, then
    suspension — and everything expires.
    """
    now = now or datetime.now(UTC)
    if last_at is not None:
        last = last_at if last_at.tzinfo else last_at.replace(tzinfo=UTC)
        if now - last > timedelta(days=90):
            upheld_against = 0
    return {
        "upheld": upheld_against,
        "warned": upheld_against >= 1,
        "daily_application_cap": 5 if upheld_against == 2 else None,
        "suspended": upheld_against >= 3,
    }

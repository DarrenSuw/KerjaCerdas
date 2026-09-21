# Trust & Verification (email OTP, skill proof, AutoMod)

> **v2 change:** the mock e-KYC surfaces (`/verify/identity`, `/verify/education`, `/verify/npwp`,
> `/verify/documents`) and the SMS OTP demo were **removed**, and the `seekers.nik`,
> `seekers.nik_verified`, `seekers.ijazah_verified` and `employers.npwp` columns were dropped
> (migration `a2b4c6d8e0f1`). A format check that cannot confirm anything was not worth the UU PDP
> liability. Identity documents are checked by the employer at the interview, as they already are.

What the platform verifies now, it verifies itself.

---

## 1. Email ownership — `backend/app/api/routers/verify.py`

| Endpoint | Purpose |
|---|---|
| `GET /verify/status` | `{ email, email_verified }` |
| `POST /verify/email/send` | 6-digit code, valid 10 min, 5 attempts, rate limit 5/60 s |
| `POST /verify/email/verify` | Sets `users.email_verified` |

- Codes are stored as SHA-256 hashes (`code_hash=_hash_token(code)`) in the `otps` table; the column
  that used to hold a phone number is now `destination` (the email address).
- Delivery: Resend HTTP API when `RESEND_API_KEY` is set (`services/email/sender.py`). Without a
  provider the code is returned in the response **only** while `otp_demo_enabled` (never in production
  by default); otherwise the endpoint fails closed with `503`/`502` rather than pretending to send.

## 2. Skill proof — `services/quiz/`, `services/matching/evidence.py`

| Proof level | Earned by | Weight in the skill part of the score |
|---|---|---|
| `claimed` | written in the CV/profile | 0.30 |
| `quiz` | passed a skill quiz — valid 180 days | 0.85 |
| `hr_confirmed` | employer ticked "terbukti" after an interview | 1.00 |

Integrity rules (all enforced server-side):

- The answer key never leaves the server. `/quiz/start` returns questions with **per-attempt shuffled
  options** (`option_order(attempt_id, question_id)`) and no correct index; grading re-derives the same
  permutation on submit.
- A deadline is stored on the attempt (45 s per question + grace); a late submission scores 0.
- An unsubmitted attempt inside its deadline is **resumed**, so reloading cannot draw fresh questions.
- Failed attempt → cooldown (7 days; 2 with Prism). Passing writes a `skill_evidence` row and updates
  the seeker's skill.
- Clients cannot forge proof: the API skill input has no proof field; the agent's inline-profile
  override resets every proof level and re-copies real proof from the stored profile; and
  `evidence.carry_proof` keeps earned badges when a profile edit or CV re-upload replaces the skill list.
- Honest limit, stated in-product: a remote quiz is not cheat-proof. The interview kit asks the
  candidate to explain their own answer, and HR confirmation is the final gate.

## 3. Employer trust badges — `services/trust/policy.py`

| Badge | How it is earned |
|---|---|
| `email_verified` | email OTP |
| `company_email` | verified email whose domain matches the company website (free mail providers never qualify) |
| `admin_reviewed` | an admin checked the public proof links submitted via `POST /employer/trust/review-request` (Google Maps, Instagram business, website) |

A badge of `company_email` or `admin_reviewed` also skips the first-job hold.

## 4. AutoMod for job ads — `services/trust/automod.py`

- **Hard rule → `rejected` + strike:** asking candidates to pay (training, uniform, administration…).
- **Soft rules → `held` for admin review:** age limits, appearance requirements, gender-only wording
  without a stated reason, Telegram-only contact, salary far outside a sane range.
- **Optional AI layer** (only when a Gemini key exists) may *hold*, never reject on its own.
- Every reason carries `{rule, severity, excerpt, fix}` so the poster notice can quote the exact
  sentence and say how to fix it; the poster can edit & resubmit or appeal.
- **Strike ladder** (`strike_state`): 1 warning → 2 limited to one active job for 30 days → 3 suspended;
  strikes expire 90 days after the last one.
- **Candidate reports** (`POST /public/jobs/{code}/report`, one per user per job): once
  `MODERATION_REPORT_THRESHOLD` distinct unresolved reports exist, the job is hidden for review.
- Invariant kept in one place (`policy.set_moderation`): a job that is not `published` is always
  `is_active = False`, so every existing `is_active` filter hides it.
- Everything is written to `moderation_events` as an audit log.

## 5. What is deliberately not collected

NIK/KTP, ijazah numbers, NPWP, and phone numbers for OTP. Emails, phone numbers and 16-digit NIKs found
inside an uploaded CV are redacted by fixed rules before storage and before any LLM call
(`services/privacy/redact.py`).

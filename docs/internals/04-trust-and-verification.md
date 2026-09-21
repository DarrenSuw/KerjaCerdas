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
- Failed attempt → cooldown of **1 day, identical on every plan**. Prism used to cut it to 2 days,
  which meant money shortening the route to a badge that moves a match score — the one thing paying
  must never do. The cooldown was never the real defence anyway; bank size is.
- Clients cannot forge proof: the API skill input has no proof field; the agent's inline-profile
  override resets every proof level and re-copies real proof from the stored profile; and
  `evidence.carry_proof` keeps earned badges when a profile edit or CV re-upload replaces the skill list.
- **Only reviewed questions can grant proof.** `find_active_questions()` filters on `active` AND
  `reviewed`, and `list_quiz_skills()` filters identically — when those two predicates disagree the UI
  offers an "Ikut kuis" button for a skill whose quiz then 404s.
- **A retake never repeats the previous attempt.** `_pick_questions()` excludes the last submitted
  attempt's question ids outright, and the one before that when the bank still leaves a real choice.
  It never raises on a thin bank: an unfinished bank is our failure, not the candidate's.
- **The bank targets 30 questions per skill** (`generator.BANK_TARGET`) and tops itself up. Below 10 a
  skill cannot even give two consecutive non-overlapping quizzes.
- **Generated questions are screened mechanically, not trusted.** `validate_question()` rejects
  malformed items, duplicate options, out-of-range keys, combination answers ("semua benar") and the
  classic giveaway of a correct answer far longer than every distractor. Passing items are served as
  `source="ai_auto"`; failing ones are stored inactive as `"ai_draft"` for a human. `source` exists so
  that "reviewed" can never be mistaken for "a practitioner approved this".
- **Generation is gated on the claim.** A skill with no bank costs ~Rp85-130 of Gemini to create, so
  only a skill already on the seeker's profile may trigger it — otherwise any logged-in user could
  loop invented names and bill us per name while gaining nothing. Skills that already have a bank stay
  open to everyone, because taking the quiz is how you earn the skill and it costs Rp0.
- **A skill with no bank is queued, not improvised.** The first request drafts questions once
  (`reviewed=False`) and returns "kuis sedang disiapkan"; the skill stays `claimed` (0.30) until an
  admin approves the batch, which then goes live for everyone holding that skill. Serving unreviewed
  questions would mean a mis-keyed answer marking correct answers wrong with no way to notice, two
  candidates never sitting a comparable quiz (which is what a 0.85 weight has to mean), and a
  candidate being able to invent a skill name to summon a fresh unvetted quiz of their own. Demand is
  logged as a `quiz_unavailable` event so the queue is worked in the order seekers actually ask.
- **Generation dedupe counts ACTIVE rows, reviewed or not.** Reviewed-only would never see a freshly
  generated batch and would re-bill Gemini on every attempt; all-rows would let deactivated questions
  wedge a skill below the serveable threshold forever.
- Honest limit, stated in-product: a remote quiz is not cheat-proof. The interview kit asks the
  candidate to explain their own answer, and HR confirmation is the final gate. The starter bank is
  currently **8 skills x 6 questions, AI-drafted** — `C(6,5) = 6` distinct quizzes per skill, so a
  retake shows at least 4 questions already seen. Expanding it is tracked in ROADMAP §3.6.

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
- **Candidate reports** (`POST /public/jobs/{code}/report`, one per user per job) are **weighted, not
  counted** (`services/trust/rules.py`). A report names the published rule it alleges was broken;
  reporter weight comes from verified email, account age, whether they actually applied, and whether
  their past reports held up. Reaching `FLAG_WEIGHT_THRESHOLD` sets the posting to `flagged`, which
  **stays publicly visible** — then the AI reviewer checks the posting against the cited rule only and
  may answer LANGGAR / TIDAK / RAGU. Only LANGGAR hides it; anything else queues a human.
  The old rule (N distinct reports → hidden) let three throwaway accounts remove a competitor's advert
  with nothing checked, while a real scam stayed live until a third person happened to complain.
- Invariant kept in one place (`policy.set_moderation`): a job that is not `published` is always
  `is_active = False`, so every existing `is_active` filter hides it.
- Everything is written to `moderation_events` as an audit log.

## 5. What is deliberately not collected

NIK/KTP, ijazah numbers, NPWP, and phone numbers for OTP. Emails, phone numbers and 16-digit NIKs found
inside an uploaded CV are redacted by fixed rules before storage and before any LLM call
(`services/privacy/redact.py`).

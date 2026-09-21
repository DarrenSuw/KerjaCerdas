# Scoring, HR feedback & plan economics — the precise version

Every claim here is checked against code, with the file and the guard test that
keeps it true. If a statement in a pitch, a slide or a README disagrees with
this file, this file is right and the other one is stale.

Files:
- `backend/app/services/matching/matcher.py` — the four weights
- `backend/app/services/matching/evidence.py` — per-skill proof scoring
- `backend/app/services/quiz/` — how proof is earned
- `backend/app/api/routers/employer.py` — pipeline + rejection feedback
- `backend/app/services/billing/plans.py` — what each plan buys
- `docs/RULES.md` — the published moderation rulebook

---

## 1. The score

```
skor = 0,35 x kemiripan teks (cosine)
     + 0,40 x skill terbukti
     + 0,15 x pengalaman
     + 0,10 x pendidikan
```

`_W_SKILL > _W_COSINE` is the load-bearing invariant. Cosine is the term keyword
stuffing inflates, so proof must outweigh it or the product's headline claim is
false. Guard: `TestProofBeatsKeywordStuffing`, `TestDisplayedWeightsMatchTheEngine`.

Worked, with experience and education held equal:

| Candidate | cosine | proof | total |
|---|---|---|---|
| CV copied from the advert, all skills claimed | 0.90 | 0.30 | **0.685** |
| Quiz-proven, mediocre text match | 0.50 | 0.85 | **0.765** |
| CV copied, **perfect** text match | 1.00 | 0.30 | **0.720** |

Bands: `strong >= 0.65`, `possible >= 0.45` (`settings.band_*_threshold`). Note
the honest consequence: the stuffer at 0.685 is still `strong`. **We do not block
liars, we rank them below proof.** Say that before a judge finds it.

## 2. The skill term is per-skill, and the denominator is the JOB's list

`evidence._coverage()` divides by the number of skills **the job asked for**, not
by the number the candidate claims:

```python
sum(PROOF_WEIGHTS[held[k]] if k in held else 0.0 for k in keys) / len(keys)
#                                                                  ^ job's required skills
```

Consequences, all of them intentional:

- **Claiming 20 skills gives no advantage over claiming 3.** Padding a profile
  cannot move the score, because the denominator does not grow with the claims.
- **A skill outside the job's list is worth exactly zero** to that job. It is not
  a penalty and not a bonus; it simply is not in the sum.
- **Candidates with different numbers of claimed skills are directly comparable**,
  because every one of them is scored against the same denominator — the job's.
- Required skills carry **80%** of the skill term and nice-to-have **20%**
  (`_REQUIRED_SHARE = 0.8`).

This answers the panel note "feature weights should be per skill". It was already
true; what is **not** yet built is showing the per-skill breakdown to HR. The data
exists per skill (`evidence.proof_map()` returns `{skill_key: proof_level}`) and
is already persisted on the application as `skill_snapshot`. **That gap is UI
work, not algorithm work.** Do not re-derive the scoring to fix a display.

## 3. Proof levels and expiry

| Level | Earned by | Weight |
|---|---|---|
| `claimed` | written in the CV/profile | 0.30 |
| `quiz` | passed the skill quiz | 0.85 |
| `hr_confirmed` | employer ticked "terbukti" after an interview | 1.00 |

A quiz badge **expires after 180 days** and reverts to `claimed`
(`QUIZ_VALID_DAYS`, `effective_proof()`). This **is** the recency mechanism the
panel asked for — a cliff rather than a decay. The same notes also asked for
verified skills to be permanent; those two requests contradict each other and one
has to be dropped. Making badges permanent removes recency entirely.

`evidence.carry_proof()` preserves earned badges when a profile edit or a CV
re-upload replaces the skill list, and the agent's inline-profile override resets
every proof level before re-copying real proof from storage. A client can never
assert its own proof level: the API skill input has no proof field.

## 4. Earning proof: the quiz

- 5 questions per attempt, pass at 4/5, 45 s per question plus grace.
- Graded against a local answer key — **no AI call, Rp0 per attempt**. This is why
  quizzes can be unlimited and free on every plan.
- Guess-through probability with 4 options and a 4/5 pass mark: **1.56%**
  (`C(5,4)·0.25⁴·0.75 + 0.25⁵`). Not zero, which is part of why a quiz is worth
  0.85 and only HR confirmation is worth 1.00.
- Option order is shuffled per attempt and re-derived on submit; the key never
  leaves the server.
- **Retake cooldown is 1 day, identical on every plan.** It used to be 7 free / 2
  with Prism — money shortening the path to a badge that moves a score. Guard:
  `TestPayingNeverBuysProofOrLessService`.
- **A retake never repeats the previous attempt's questions**
  (`service._pick_questions`), and avoids the attempt before that when the bank
  still leaves a real choice. When the bank is too small to honour the rule it
  serves anyway, filling the unavoidable remainder with the questions seen
  *longest ago* — a candidate must never be locked out because our bank is
  unfinished — **but that attempt cannot award a badge**
  (`QuizAttempt.proof_eligible = False`). It is scored and shown like any other
  quiz; it simply never reaches `skill_evidence` and never lifts `proof_level`.
  Passing questions you were shown yesterday is not evidence of the skill, and
  the badge carries a 0.85 weight straight into the match score. Reporting the
  overlap was the first attempt at this and was not a fix: visibility is not
  mitigation when the harm is the badge itself. The candidate is told plainly
  why, and the next attempt is clean once the bank refills.
- **Bank target: 30 questions per skill** (`generator.BANK_TARGET`), topped up
  automatically. Below 10 a skill cannot give two consecutive non-overlapping
  quizzes at all.
- Generated items pass `validate_question()` — a mechanical check, no AI — and are
  stored as `source="ai_auto"` when they pass, inactive `"ai_draft"` when they do
  not. **`source` exists so that "reviewed" is never read as "a practitioner
  approved this".** Never describe an `ai_auto` question as practitioner-reviewed.
- Generation is gated on the claim: a skill with **no** bank costs ~Rp85–130 to
  create, so only a skill already on the seeker's profile may trigger it. Skills
  that already have a bank stay open to everyone. Generation is additionally
  throttled per skill (15 min cold, 6 h for top-ups).

## 5. HR feedback

| Transition | Feedback |
|---|---|
| → hired / interview / offered | optional |
| → **rejected** | **`reason_code` required (HTTP 422 without it)** |

Codes (`employer.REJECTION_REASONS`): `skill_kurang`, `pengalaman_kurang`,
`lokasi`, `gaji`, `posisi_terisi`, `tidak_hadir`, `dokumen`, `lainnya`.

Fixed codes rather than a free-text box, for two reasons: HR can finish in one
tap (an empty textarea gets skipped), and the result is **countable**. Stored on
`application_status_events` alongside the `match_score` at the moment of the
transition, which makes this the only structured dataset that can ever test
whether a high score actually predicts reaching an interview.

HR skill confirmation (`POST /applications/{id}/confirm-skills`) is only allowed
once the application has reached a post-interview status — you cannot tick
"terbukti" for someone you never met.

## 6. What each plan buys, and why the paywall sits where it does

Ranking costs **Rp0** to compute. Capping it therefore saved nothing and only hid
the candidate ranked 21st from the employer who asked for a ranking, so ranked
applicants are **uncapped on every tier including free**
(`spark_ranked_applicant_limit = 0`).

The quota sits on **reverse matching** — searching candidates who have *not*
applied. That is sourcing rather than screening, it is the thing an employer will
actually pay for, and limiting it hides nobody who asked to be seen.

| Plan | Price | Quota that matters |
|---|---|---|
| Spark | Rp0 | 1 active job, all applicants ranked, 0 talent searches |
| Beacon | Rp49.000 / job / 30 d | interview kits, CSV, 30 talent searches |
| Lighthouse | Rp149.000 / 30 d | 5 active jobs, 150 talent searches |
| Seeker free | Rp0 | unlimited quizzes, 10 advisor msgs/day |
| Prism | Rp15.000 / 30 d | exact application rank + score breakdown, 20 advisor msgs/day |

**Invariant: a paid tier must be a strict superset of free on every axis it
touches.** Prism was once 100 messages / 30 days against a free 10 / day — 100 a
month against 300, with a 30-day lockout instead of an overnight one. Paying
bought less. Guard: `test_the_paid_advisor_quota_is_larger_on_the_same_axis`.

### The advisor ceiling is priced, not guessed

| Cap | Messages / 30 d | Flash-lite (~Rp13,5) | Fallback `gemini-3.6-flash` (~Rp57) |
|---|---|---|---|
| 20/day (shipped) | 600 | Rp8.100 → **46% margin floor** | Rp34.200 → loss |
| 30/day (rejected) | 900 | Rp12.150 → 19% | Rp51.300 → heavy loss |

Break-even at Rp15.000 is **1.111 messages** on flash-lite and **263** on the
fallback model — 37/day versus 8,8/day. `llm_factory.chat_model_chain()` **does**
fall back to `gemini-3.6-flash`, so the cap has to survive the fallback path and
not merely the happy one. **Open risk:** a sustained fallback makes even 20/day
unprofitable at the ceiling. The structural fix is metering by cost rather than by
message count; until that exists, this is a monitored exposure, not a solved one.

## 7. Contribution per sale

Assumptions marked as such; token counts per action are assumptions verified
against real `ai_logs` at `/admin → Metrik`. Buffer ×1,5 throughout.

| Item | Price | COGS | Contribution | Margin |
|---|---|---|---|---|
| Beacon (1 job) | Rp49.000 | ~Rp3.400 | **Rp45.600** | **93%** |
| Lighthouse (~3 jobs) | Rp149.000 | ~Rp10.250 | **Rp138.750** | **93%** |
| Prism, typical use | Rp15.000 | ~Rp2.500 | **Rp12.500** | **83%** |
| Prism, ceiling (flash-lite) | Rp15.000 | ~Rp8.100 | **Rp6.900** | **46%** |
| Spark (free job) | Rp0 | ~Rp1.900 | −Rp1.900 | acquisition |
| Free seeker / active month | Rp0 | ~Rp310 | −Rp310 | acquisition |

Interview-kit caching lowers the Beacon figure further; it is left conservative.
Reverse matching is a pgvector query and costs **Rp0** in AI terms.

## 8. Things that are true today and easy to get wrong

- Paying changes **no** score and **no** rank. Prism buys visibility *into* your
  own result (exact rank, per-component breakdown) and a bigger advisor quota.
  It does not buy a badge, a faster badge, or a better position.
- Quizzes, match scoring, ranking, applying and badges are all **Rp0** to serve.
  They are unlimited and free deliberately, not as a promotion.
- A flagged posting is **still visible**. Only a verdict against a **hard** rule
  hides one automatically; soft-rule findings go to a human. See `docs/RULES.md`.
- The starter question bank is AI-drafted. `source` distinguishes `human` from
  `ai_auto`; practitioner review of the bank is **not** done.

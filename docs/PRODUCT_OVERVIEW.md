# Product Overview

## Problem

Conventional recruitment channels — keyword-based job portals, manual forms, spreadsheets — fail to capture semantic equivalence between job terms ("backend engineer" vs. "software developer" read as unrelated to a keyword matcher) and give job seekers no concrete direction on what to improve. On the employer side, small and mid-sized companies without an enterprise ATS budget have to screen recruiting volume by hand.

Four root causes drive this:
1. **Relevance mismatch** — keyword search treats semantically equivalent job terms as unrelated.
2. **Visibility gap** — candidates don't know which specific skills are keeping them out of a role.
3. **Screening fatigue** — HR teams without an ATS filter applications manually, one at a time.
4. **Unverifiable claims** — a CV is a claim, not evidence. AI-written CVs make keyword-shaped profiles trivial to produce, so ranking CV text alone hands HR *more* noise, not less. This is the gap v2 closes.

National context: Indonesia's official open unemployment rate (TPT) was 4.65% as of May 2026, with average worker pay at Rp 3.39 million ([BPS, released 5 August 2026](https://www.bps.go.id/id/pressrelease/2026/08/05/2606/tingkat-pengangguran-terbuka--tpt--sebesar-4-65-persen---rata-rata-upah-buruh-sebesar-3-39-juta-rupiah-.html)).

## Users

- **Job seekers (B2C):** fresh graduates and recent vocational/university graduates (SMK, Politeknik, D3/S1), typically 18–25, who struggle to identify relevant openings and their own skill gaps.
- **Employers (B2B):** HR teams at SMEs, startups, and mid-sized companies without budget for enterprise ATS licenses, dealing with a high volume of irrelevant applications.
- **Potential partners:** ed-tech course providers, for referral-based skill-gap recommendations (no affiliate contracts in place yet — this is a roadmap item, not a current integration).

## Core Use Case

```
Candidate doesn't know which openings fit them
  → Upload CV (PDF)
  → Gemini extracts skills/experience/education → 768-dim embedding → pgvector HNSW search
     → Hybrid ranking (cosine 35% + proof-weighted skills 40% + experience 15% + education 10%)
       where a skill counts 0.30 if only claimed in the CV, 0.85 once a skill quiz is passed,
       and 1.00 once an employer confirms it after an interview
  → Result: banded job list (Strong/Possible/Stretch) with a per-factor breakdown and, per skill,
     whether it is claimed / quiz-proven / HR-confirmed
  → Outcome: candidate picks a job with a reason, and knows exactly which skill to prove next
```

For a target job that isn't a full match, the flow continues into the **Skill Gap Analyzer**: the skill gap is computed deterministically, then Gemini narrates a learning plan and recommends courses from a curated internal catalogue.

On the employer side: **company profile → post a job (AutoMod checks it) → share its link / QR poster where they already recruit → applicants arrive in one list ranked by proof-weighted score → AI interview questions for skills that are still only claimed → after the interview, HR ticks "skill terbukti", which becomes the strongest proof on that candidate's profile.**

See [Architecture](ARCHITECTURE.md) for the full system diagram, and [Sequence Diagrams](SEQUENCE_DIAGRAMS.md) for the request-level flows.

## Differentiation

| Dimension | Conventional job portal (keyword) | Manual/spreadsheet process | KerjaCerdas |
|---|---|---|---|
| Matching | Exact/keyword match | Manual, subjective | Semantic embedding + 5-factor hybrid ranking |
| Score transparency | None | None | Explainable AI breakdown per factor |
| Skill direction | None | None | Skill Gap Analyzer with targeted course recommendations |
| Skill evidence | None — CV text is taken at face value | Ad-hoc, per recruiter | Short skill quizzes (✓ Terbukti, 180 days) + HR confirmation, weighted into the score |
| Scam / discriminatory ads | Reported manually, if at all | — | AutoMod blocks fee-charging ads, holds discriminatory ones, notifies the poster with the exact sentence + appeal |
| Employer cost | Expensive upfront ATS subscription, or free with no AI | High manual screening time | Free to post (Spark); Rp29k per job (Beacon) or Rp99k/month (Lighthouse). Never charged for contact details |

## Current Scope

**Works today:** proof-weighted semantic matching, skill quizzes with ✓ Terbukti badges, shareable job links + printable QR posters, public apply page, AutoMod for job ads with poster notices/appeals/strikes, candidate reports, email OTP verification, AI interview questions + HR skill confirmation, anonymised talent pool, applicant CSV export, plan limits (Spark/Beacon/Lighthouse/Prism), admin panel (moderation, business review, plan activation, question bank, metrics), skill-gap analysis, application tracking, A/B assignment and event logging.

**Demo / manual mode:** plan payments (QRIS or bank transfer confirmed by an admin — no payment gateway yet); the starter quiz bank ships as a draft pending review by HR practitioners; email OTP falls back to returning the code in the response when no email provider is configured (never in production).

**Deliberately not collected:** NIK/KTP, ijazah numbers, NPWP. Identity is checked by the employer at interview, as it already is in practice.

**Not yet built:** production payment gateway (Midtrans/Xendit), score calibration against real hiring outcomes (the data is being recorded now), ed-tech affiliate agreements, enterprise ATS integrations.

## Business Model

See [Business Model](BUSINESS_MODEL.md) for the full monetization structure, cost breakdown, and financial projections. In short: employers post for free and pay per job (Beacon Rp29k) or per month (Lighthouse Rp99k) to rank every applicant and get AI interview questions; job seekers stay free, with an optional Prism plan (Rp25k / 30 days) that only buys quota and shorter retake cooldowns — never a better score. Ed-tech affiliate income is upside only and is excluded from break-even.

## Adoption Path

A narrow pilot — entry-level roles (admin, customer service, cashier, sales, warehouse) with SME employers in Jabodetabek — before wider rollout. The dependencies for scaling past the pilot are a production payment gateway and a quiz bank reviewed by HR practitioners; see [Roadmap](ROADMAP.md).

## Team

| Member | Role | Focus |
|---|---|---|
| David Kurniawan | Project Lead & AI Engineer | System architecture, semantic matching engine, LangGraph pipeline, pgvector, end-to-end reliability |
| Darren Cornelius Suwandi | Product Manager, UI/UX, Research | Product vision, UX design, problem validation, market research |
| Vanessa Serenina Prawirayasa | System Analyst & Impact Strategist | Backend-to-product flow architecture, KPI and impact metric design |
| Jason Clarence Setya Budhi | Business/Market Strategist, Backend & Integration | Monetization, go-to-market, API integration, cloud deployment |

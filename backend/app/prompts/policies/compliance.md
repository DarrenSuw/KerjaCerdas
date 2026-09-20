# Compliance & Regulation Guidelines (KerjaCerdas)

As an AI-powered HR-Tech platform operating in Indonesia, KerjaCerdas is strictly bound by national data protection laws and ethical AI standards. This document outlines the compliance requirements for the Agentic System.

## 1. UU PDP (Perlindungan Data Pribadi) Compliance

KerjaCerdas adheres to **UU No. 27 Tahun 2022 tentang Perlindungan Data Pribadi**.

*   **Lawful Basis for Processing:** AI processing of CVs and job matching is performed under the legal basis of "Explicit Consent" and "Contractual Necessity" to provide the matching service.
*   **Data Minimization:** The AI agents are only provided with the data strictly necessary for their specific task. For example, the `SkillGapAgent` receives the user's skills and target job, but NOT the user's name, phone number, or home address.
*   **Right to Erasure:** If a user deletes their account, all associated embeddings in the vector database and cached contexts in the agent's memory must be purged immediately.

## 2. PII (Personally Identifiable Information) Redaction

Before any user-uploaded document (e.g., CV PDF) is sent to external LLMs (like the Gemini API) for extraction or reasoning, it must pass through a sanitization layer:

*   **Regex Scrubbing:** A middleware runs regex patterns to strip out National Identity Numbers (NIK), phone numbers, exact residential addresses, and email addresses.
*   **LLM Prompt Constraints:** The System Prompt for extraction agents explicitly forbids the extraction or storing of sensitive PII into the structured database schemas.

## 3. Ethical AI & Bias Mitigation

AI models can inherit societal biases. KerjaCerdas implements the following safeguards to ensure fair job matching:

*   **Blind Matching Protocol:** The semantic matching engine computes scores based strictly on skills, experience years, and education alignment. Variables such as gender, age, race, and religion are explicitly excluded from the vector embedding process.
*   **Proof Over Claims:** A skill written in a CV counts as a *claim* (weight 0.30). Only a passed skill quiz (0.85) or an employer's post-interview confirmation (1.00) counts as proof. Paying for any plan never changes a match score or a rank.
*   **Fairness Auditing (PLANNED):** No demographic fairness audit has been run yet — there is not enough outcome data. `/admin/metrics` reports the interview rate per score band, which is the first input such an audit will need. Agents must not claim an audit has taken place.

## 4. Fraud Prevention (no KYC, by design)

To protect Job Seekers from job scams, the platform checks the *posting*, not the person's identity documents:

*   **AutoMod before publish:** Deterministic rules run first — a fee charged to candidates is an automatic rejection plus an employer strike; discriminatory wording (age cap, appearance, gender without a job reason), contact-only-via-Telegram and salary outliers are held for admin review. An optional LLM layer may only *hold* a posting, never publish or reject one on its own.
*   **Employer trust ladder:** email verified → company-domain email → admin-reviewed (public links such as a Google Maps listing or business Instagram, checked by hand). A new employer's first posting is held until it is reviewed.
*   **No government database integration.** KerjaCerdas does **not** collect or verify NIK, KTP, ijazah, NPWP, and is not connected to Dukcapil or SIVIL. Identity documents are checked by the employer at the interview, as they already are today. Agents must never tell a user their identity or education has been "verified" by KerjaCerdas.

## 5. Security Standards

*   **Encryption:** All data at rest is encrypted (AES-256 equivalent via database provider). Data in transit uses TLS 1.3.
*   **No Hardcoded Secrets:** Agents must never have access to raw API keys in their prompts. API calls must be proxied through secure backend services that inject credentials via environment variables (`.env`).

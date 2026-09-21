# CV Upload & Parsing

Files:
- `backend/app/api/routers/uploads.py` — endpoint, validation, IDOR guard
- `backend/app/services/pdf_parser.py` — text-first extraction + Gemini + offline fallback
- `backend/app/services/privacy/redact.py` — the fixed regex rules

## Flow — `POST /api/v1/uploads/cv`

```
PDF upload (≤10 MB, application/pdf only, must start with %PDF- magic bytes)
        │  auth: require_seeker — the seeker profile is always resolved from
        │  the caller's own JWT (find_seeker_by_user_id); no profile id is
        │  ever accepted from the client, so there is nothing to IDOR
        ▼
pdf_parser.parse_cv(blob, allow_scanned=<explicit consent>):
  1. Truncate to the first 3 pages (_MAX_GEMINI_PAGES) — Gemini bills
     multimodal PDFs per page, so this caps per-upload cost.
  2. Extract the text layer locally (PyMuPDF), then REDACT it: email,
     phone and 16-digit NIK are replaced by fixed regex rules before
     anything leaves the server.
  3. Send the redacted TEXT to Gemini, walking a model fallback chain
     with a 30s timeout and one retry per model, demanding structured
     JSON per tasks/cv_parser.md's schema.
  4. _validate_cv_schema() coerces every field, and redacts resume_text
     again — whatever the model echoes back can still contain contact
     data it read off the CV.
        │
        ├─ text layer < _MIN_TEXT_TO_PARSE (200 chars) ─────────────────┐
        │                                                               │
        │  no API key, non-quota failure, timeout, malformed JSON       │
        ▼                                                               │
_fallback_extract(): PyMuPDF + regex/vocabulary heuristics for name,    │
  headline, skills (~90-word vocabulary), education year and degree     │
  level; also redacts the stored resume_text. Tagged "_offline": true.  │
        │                                                               │
        ▼                                                               │
uploads.py: _offline and not confirm_offline → 200 with                 │
  {"requires_confirmation": true, "preview": {...}} — the client shows  │
  what the heuristic produced and the seeker decides whether to accept  │
  it. Nothing overwrites the existing profile until they do.            │
        │                                                               │
        ▼                                                               │
map to SeekerProfile → SemanticMatcher.embed_seeker() → persist         │
                                                                        │
  ScannedPdfError ◄─────────────────────────────────────────────────────┘
        ▼
uploads.py: 200 with {"requires_scan_consent": true, "message": ...}
  The client explains exactly what would be sent and offers "lanjutkan"
  or the manual form. Only a re-upload with confirm_scanned=true passes
  allow_scanned=True, which is the ONLY way raw PDF bytes are ever sent.
```

## Key Design Points

- **Text-first, not native-PDF.** The text layer is extracted locally and PII-redacted *before* the call, so the phone number and e-mail printed on a CV never leave the server in the normal path. This is the opposite of the original design, which sent the PDF as a document blob; it was changed because redaction that depends on asking the model nicely is redaction that can fail.
- **Redaction is regex, not prompting.** `redact_text()` applies fixed rules. Prompt instructions are defence in depth, never the mechanism — that distinction is the answer to the judges' "redaksional berbasis prompt bisa gagal?".
- **Redacted twice.** Once on the way out (input to Gemini) and once on the way back (`_validate_cv_schema` → `resume_text`). The second pass matters because `matcher._build_seeker_text()` feeds stored `resume_text` straight to the embedding API, a path that never goes through `llm_factory.redact_llm_input`.
- **Scans need consent, not rejection.** A PDF with no usable text layer cannot be redacted, so it can only be sent as an image. Refusing it outright would exclude the many Indonesian seekers whose CV is a phone photo; sending it silently is what the redaction exists to prevent. So `_llm_contents` raises `ScannedPdfError`, the endpoint asks, and only an explicit `confirm_scanned` re-upload sends the image. Explicit consent is also the correct UU PDP lawful basis.
- **`ScannedPdfError` bypasses the fallback.** `_call_gemini` otherwise converts any exception into offline/demo data so an upload never crashes. That handler explicitly re-raises this one — returning stub content here would hand the caller a fabricated CV (or, for job packs, a fabricated job posting) marked as a successful parse.
- **The offline heuristic is reachable, and gated.** It runs when Gemini is unavailable, and the endpoint returns a *preview* for confirmation rather than silently storing a lower-quality profile.
- **Cost caps.** 3 pages max, 30s per model attempt, one retry, then the next model in `gemini_chat_fallback_models`.
- **Immediate re-embedding.** The profile embedding is regenerated in the same request, so the next match already reflects the new CV. No background job, no staleness window.
- **Validation:** content type, `%PDF-` magic bytes, and `MAX_PDF_BYTES = 10 MB`, all enforced before any parsing.

## Failure Modes

| Scenario | Behavior |
|---|---|
| Scanned / photographed PDF, no consent yet | **200** `requires_scan_consent` — client prompts; manual form offered as the alternative |
| Same file re-uploaded with `confirm_scanned=true` | Raw PDF bytes sent to Gemini; returned `resume_text` still redacted before storage |
| Text layer under 200 chars but non-empty | Same consent prompt, different wording (*"teks terlalu sedikit"*, not *"hasil pindai atau foto"*) — a sparse PDF is not a photo |
| No `GEMINI_API_KEY` / all models fail / malformed JSON | `_fallback_extract` runs; endpoint returns **200** `requires_confirmation` with a preview, not a silent overwrite |
| Non-PDF, missing `%PDF-` header, or >10 MB | 4xx before any parsing |
| Embedding call fails after a successful parse | Profile still saved (`embed_seeker` leaves the row unembedded rather than raising); match quality degrades until the next re-embed |
| Job pack (`/uploads/job-pack`) that is a scan | **422** — no consent handshake. A job pack is the employer's own text, not a candidate's personal data, and they can paste it instead |

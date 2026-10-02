# Privacy and data lifecycle

## 1. Roles
- The **employer (workspace)** is the controller of candidate data it collects through its pipelines.
- **FastHyr** is the processor for that data (DPA with each customer), and controller for its own account, billing, marketing-site and demo data.
- **Sub-processors:** Supabase (DB, auth, storage), Vercel (web hosting), Render (API/worker hosting), OpenAI (AI processing), Stripe (payments), Resend (email), Sentry (error monitoring). Listed publicly on the Privacy page with locations.

## 2. Data inventory
| Data | Source | Purpose | Where | Default retention |
|---|---|---|---|---|
| Candidate identity (name, email, avatar) | Google/Microsoft sign-in | Application, communication | `candidates`, Supabase Auth | 24 months after last activity in that workspace |
| Contact details (phone, city, profile URL) | Apply form | Employer contact | `candidates` | same |
| Résumé PDF + extracted/redacted text | Apply form | Screening, interview plan, TA review | `resumes` bucket, `resume_assessments` | same |
| Recording (video/audio) | Interview | Assessment, TA review | `recordings` bucket | 12 months after the interview |
| Transcript, assessment, flags | Derived | TA review | DB | with candidate data |
| Face embeddings | Derived during integrity check | Same-face check | memory only | not stored |
| Consent records, AI decision log | System | Compliance | DB | life of application + 3 years (minimal after deletion) |
| Interview feedback rating | Candidate | Product improvement | DB | 24 months, not shared with employer |
| TA user account data | Sign-in | Service | Auth, `profiles`, members | account lifetime + 30 days |
| Billing details | Admin | Invoicing | Stripe + `billing_details` | as required by tax law (typically 7–10 years) |
| Demo résumé/JD | Demo visitor | Demo only | `demo_sessions`, `demo` bucket | hard-deleted ≤ 24 h |
| Contact form | Visitor | Sales follow-up | `contact_requests` | 24 months |

Retention periods are defaults to confirm with counsel; later they become workspace settings (post-MVP).

## 3. Notices and consent (FR-COMP-01)
Versioned texts stored in `apps/api/app/compliance/notices/` with version IDs saved on each record:
- **Apply consent** (apply form): employer reviews application with FastHyr; AI screens the résumé against job-related criteria; if matched, AI interview by video/voice that is recorded and shared with the employer's hiring team; a person makes hiring decisions; how to request review, accommodation or deletion; link to Privacy and AI-in-hiring pages.
- **Interview consent** (device check): talking with an AI interviewer; recorded; shared with the employer; what is evaluated; integrity checks and, where video is used, a **separate biometric consent** for the same-face check.
- **Biometric consent** (device check, video + integrity checks only): FastHyr compares the candidate's face across the session to confirm it's the same person; face data isn't stored after the check; the result never scores or rejects anyone on its own.
- **Jurisdiction add-ons** (e.g. NYC AEDT notice) appended when the pipeline's location requires it (post-OQ-4).

How versioning works (COMP-002):
- Each text is `apps/api/app/compliance/notices/<kind>@v<N>.toml` (`apply`, `interview`, `biometric`): the checkbox `statement`, the `details` shown under "What this means", `links` (`privacy`, `ai_in_hiring`, `terms`) and `choices` (wording that depends on the pipeline, such as the interview format). Placeholders are `{company}` and the `choices` keys.
- A released file is never edited. `versions.lock` holds each file's SHA-256; the API refuses to start, and CI fails, if a released file changed, lost its file or has no lock line. To change a text: copy it to the next version, edit the copy, run `cd apps/api && uv run python -m app.compliance.notices lock`, and have the change reviewed (counsel review before launch, see `AI_HIRING_REGULATIONS.md`).
- The highest version is current. `GET /v1/public/notices` serves it; older versions stay readable by number.
- When a candidate agrees, the page sends the notice id (e.g. `apply@v1`) and the API stores it with the time through `services/consents.accept()`: on `applications.consent_version / consent_at` (APPLY-003) and on `interviews.consent_version / consent_at / biometric_consent_version` (INTV-003). Agreeing to an older version is `409 notice_outdated`, so the candidate sees the current words first.
- The web renders notices only from the API with `components/consent/consent-checkbox.tsx` (never from `messages/en.json`), so the words shown are exactly the stored version's.

## 4. Candidate rights
- **Access / deletion / correction requests** go to the employer (controller). In MVP the employer's Admin deletes a candidate from the Candidates pool ("Delete candidate data", FR-COMP-05). FastHyr support can assist on request.
- Deletion removes: candidate row, applications, résumés, recordings, transcripts, assessments, flags, emails log bodies, Ava messages referencing them (redacted), storage objects. Keeps: a `deletion_requests` record and anonymised aggregate counts (e.g. funnel numbers) and `ai_decisions` rows stripped of content.
- Deletion completes within 30 days (Illinois AIVI requirement; target: immediate job, verified by the daily reconciliation).
- Demo users: nothing to request — data is gone within 24 h.

## 5. Retention jobs
`retention_purge` (daily) deletes recordings older than 12 months and candidates inactive for 24 months per workspace, logging counts to `audit_log`.

## 6. International transfers
Production data region is decided in OQ-5. Transfers to US sub-processors rely on SCCs / the Data Privacy Framework where applicable; disclosed in the Privacy Policy and DPA.

## 7. Breach response (summary)
Detect → contain → assess (which workspaces/candidates) → notify affected customers without undue delay (target ≤ 48 h so they can meet GDPR's 72 h) → remediate → post-mortem.

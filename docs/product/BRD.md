# Business Requirements Document (BRD)

## 1. Summary
FastHyr is a B2B SaaS **AI interviewer** for Talent Acquisition teams. A TA team creates a **pipeline** for a role, pastes its **apply link** into its job posts (LinkedIn, JobStreet, Indeed, careers page…), and FastHyr handles the first round automatically: **résumé screening**, a **personalised, adaptive AI interview** by video + voice or voice only, and a **structured, explainable assessment** the TA team reviews. People make every hiring decision.

Tagline: **Every applicant, heard.**

## 2. Problem
- TA teams receive hundreds of applications per role and can only read a fraction closely. Qualified people are missed because nobody got to their résumé in time.
- First-round phone screens cost hours of scheduling and are inconsistent between screeners.
- Many applicants never hear back, which damages the employer brand.

## 3. Goals and success metrics
| Goal | Metric (MVP target, to be baselined in beta) |
|---|---|
| Faster screening | Median time from application to finished assessment ≤ 2 days |
| Everyone assessed | 100% of applicants screened; ≥ 70% of invited candidates finish the interview |
| Consistency and trust | Every score shows its calculation and evidence; 0 automated rejections without a review route |
| Candidate experience | Every applicant gets a response; average post-interview rating ≥ 4 / 5 |
| Business | Trial → paid conversion; credits used per workspace per month; retention of paying workspaces |

## 4. Scope

### In scope for MVP
Everything in the design canvas (see `docs/_sources/design-canvas-inventory.md`) as adjusted by ADR-010 to ADR-018:
1. Public website: main landing, TA landing with contact form, For-candidates marketing page, pricing, terms, privacy.
2. Public interview demo.
3. TA sign-in (Google, Microsoft, email + password), workspaces (create, join, switch), user profile.
4. Getting started, Overview dashboard.
5. Pipelines: create (5-step wizard), list, lifecycle (schedule, pause, resume, close, cancel, archive, duplicate), share apply link with source tags, pipeline dashboard, candidates list, Ask Ava, locked setup view, PDF reports.
6. Public apply page with Google/Microsoft sign-in, résumé upload, consent.
7. Résumé screening with explainable fit score; automatic invite or rejection (with human-review route).
8. Personalised adaptive AI interview (OpenAI Realtime), device check, recording, transcript, reminders, resume-later, expiry, re-invite, drop-off reasons.
9. Assessment: weighted rubric scores, evidence with timestamps, summary, strengths and probes, integrity flags, candidate profile (overview, résumé, interview), candidate report PDF.
10. Candidate actions: reject (with reason), advance, email.
11. Candidates pool (workspace-wide, read-only) with dashboard and Ava.
12. Billing: plans, extra-credit packs, trial credits, invoices, credit reserves per pipeline, credit usage and ledger.
13. Workspace admin: company profile, departments, members and invites with roles, email templates with editor and history.
14. Compliance basics: notices and consent, AI decision log, human review requests, retention and deletion.

### Out of scope (MVP)
Multi-stage pipelines inside FastHyr, interview scheduling, public job board, multi-language interviews, in-app notifications, SSO/SAML for enterprises, custom rubric criteria (the three criteria are fixed; weights are editable), API/webhooks for customers. **Never:** ATS or HRIS integrations.

## 5. Stakeholders
- Product owner: Darwin Labiste.
- Build: Claude (Claude Code) under the process in `docs/process/DEV_WORKFLOW.md`.
- External: Supabase, Vercel, Render, OpenAI, Stripe, Resend (sub-processors).

## 6. Constraints
- Stack fixed by ADR-001 to ADR-009.
- Global market: GDPR, UK GDPR, CCPA/CPRA, EU AI Act (employment AI is high-risk), NYC Local Law 144, Illinois AI Video Interview Act and BIPA, Colorado AI Act. See `docs/compliance/`.
- Multi-tenant: every piece of pipeline, candidate and assessment data is scoped to a workspace.

## 7. Assumptions
- English-language roles and candidates at launch.
- Customers bring their own job-board postings; FastHyr never posts jobs.
- Résumés are text-based PDFs; scanned PDFs are handled as "couldn't read résumé" (see `REQUIREMENTS.md`).

## 8. Risks
| Risk | Mitigation |
|---|---|
| AI bias or unfair scoring | PII redaction before scoring, fixed job-related criteria, evidence required for every score, bias monitoring, human review route (`compliance/BIAS_FAIRNESS.md`) |
| Realtime voice cost and latency | 30-min cap, demo cap and rate limits, cost tracking per interview |
| Candidate drop-off (SSO-only, device issues) | Device check, resume-later, reminders, re-invite, drop-off analytics |
| Regulatory change (AI Act, US state laws) | Compliance docs owned and reviewed before launch; counsel review of notices |
| Impersonation | Integrity flags with human review; same-account sign-in for interview |

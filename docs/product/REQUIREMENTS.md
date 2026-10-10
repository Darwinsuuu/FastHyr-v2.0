# Requirements

Functional requirements are grouped by area and numbered `FR-<AREA>-NN`. Non-functional requirements are `NFR-NN`. Tasks and user stories cite these IDs. "Frame" refers to a frame in the design canvas (`docs/_sources/design-canvas-inventory.md`); "Spec" refers to `docs/design/SCREEN_SPECS.md`.

Gap-area tags (G1–G9) are defined in `CONSIDERATIONS.md`.

---

## FR-AUTH — TA authentication and workspaces
| ID | Requirement | Source |
|---|---|---|
| FR-AUTH-01 | TA users sign in with Google, Microsoft, or work email + password (min 8 chars). First sign-in creates the account. | EmployerLogin |
| FR-AUTH-02 | "Forgot password" sends a single-use reset link that expires in 1 hour; resend is allowed after 60 s; the response never reveals whether the email exists. A "Set a new password" page completes the reset. | EmployerLogin, Spec S-05 |
| FR-AUTH-03 | Email + password accounts must verify their email before creating or joining a workspace. | Spec S-06 |
| FR-AUTH-04 | After sign-in, a user with no workspace sees "Choose workspace"; a user with workspaces goes to their last active workspace. | WorkspaceSelect |
| FR-AUTH-05 | Creating a workspace makes the user its owner (Admin), grants trial credits (FR-BILL-02) and opens Getting started. | WorkspaceSelect, ADR-004 |
| FR-AUTH-06 | Joining accepts an invite link or code; the invite must be valid, unexpired, unrevoked, and addressed to the signed-in email. | WorkspaceSelect, Spec S-04 |
| FR-AUTH-07 | The workspace switcher lists every workspace the user belongs to with role and member count, plus Create and Join. | App shell |
| FR-AUTH-08 | User profile modal shows email (verified), sign-in method, last sign-in, created date, user ID with copy. Name and photo come from the identity provider. | WorkspaceSelect |
| FR-AUTH-09 | Log out ends the session on this device. | App shell |

## FR-WS — Workspace admin
| ID | Requirement | Source |
|---|---|---|
| FR-WS-01 | Admins edit the company profile: logo (SVG/PNG, square, ≥256 px, ≤2 MB), email banner (PNG/JPG, ≤2 MB), company name (required), website, industry, size, HQ country, time zone, about (≤600 chars), careers page URL. Used on the apply page, interview screens and emails. | CompanyProfile |
| FR-WS-02 | Admins create, rename and delete departments (unique name; "No department" reserved). Deleting moves its pipelines to No department and removes that access from members. | Departments |
| FR-WS-03 | Admins invite members by email with a role and departments. Invites expire after 7 days; can be resent (old link stops working) or revoked. | ManageMembers |
| FR-WS-04 | Admins change a member's role and departments (effective immediately) or remove access. The owner cannot be removed or demoted. | ManageMembers |
| FR-WS-05 | Members list shows role, departments, last active, status; filter by role and department; search by name/email. | ManageMembers |
| FR-WS-06 | Permissions follow the matrix in `architecture/SECURITY.md` (ADR-005). | ADR-005 |

## FR-DASH — Getting started and Overview
| ID | Requirement | Source |
|---|---|---|
| FR-DASH-01 | Getting started shows 5 steps with completion derived from data (profile saved, member invited or skipped, templates reviewed or skipped, credits available beyond trial or plan active, first pipeline published). | GettingStarted |
| FR-DASH-02 | Overview shows KPIs for This week / 30 days: applicants (+ change), ready for review (+ flagged), live pipelines (paused, scheduled), median time to screen (apply → finished interview). | Overview |
| FR-DASH-03 | "Needs your attention" lists: candidates ready for review (count, pipelines, oldest wait), flagged interviews, human-review requests, pipelines paused for credits, pipelines running low (<30 days of credits at current pace), plan credits expiring within 7 days, pending member invites expiring within 3 days. | Overview, ADR-015 |
| FR-DASH-04 | Overview funnel, strongest waiting candidates (top 5 by score), live pipelines closing soonest, applicants per week (8 weeks, applied vs passed), sources with pass rate, drop-off reasons (last 30 days), credits card. | Overview (G8, G1) |
| FR-DASH-05 | All dashboard numbers respect the member's department scope. | ADR-005 |

## FR-PIPE — Pipelines
| ID | Requirement | Source |
|---|---|---|
| FR-PIPE-01 | Wizard step 1 (Role): title (required), department, employment type, work setup, location, job description (required), must-haves (min 3), **nice-to-haves (optional)**, **résumé pass bar (0–100, default 60)**, "Also open to" (6 options). | NewPipeline, ADR-013 |
| FR-PIPE-02 | Step 2 (AI interview): format, tone (Warm, Professional, Direct), seniority (Entry, Mid-level, Senior, Lead), skills to probe (min 3), link expiry (3/5/7/14 days, default 5), toggles: reminder 24 h before expiry (default on), flag possible impersonation (default on). | NewPipeline (G3) |
| FR-PIPE-03 | Step 3 (Scoring): Technical fit / Communication / Culture alignment weights summing to exactly 100; pass mark 0–100 (default 70); toggles: email résumé-not-a-match candidates, email candidates after their interview. | NewPipeline (G4) |
| FR-PIPE-04 | Step 4 (Schedule & credits): open now or on a date; duration 30/60/90/120 days; reserve credits (min 10, step 10, ≤ free credits). Shows close date and reserve implications. | NewPipeline |
| FR-PIPE-05 | Step 5 (Review): summary with Edit links; publish or schedule requires typing "I understand". "Save as draft" at any step. Validation blocks Continue with a clear message. | NewPipeline |
| FR-PIPE-06 | After publish: show share tiles (FR-PIPE-10), "Go to pipelines", "Create another". | NewPipeline |
| FR-PIPE-07 | Pipeline states and transitions exactly as `WORKFLOW.md` §2, including lock on open, pause, resume, close (optional "Role closed" email to candidates who haven't heard back), cancel scheduled (reserve returned), archive, start now, duplicate as new draft. | PipelinesV2 |
| FR-PIPE-08 | Pipelines list: flow summary (week/30 days), tabs Live/Scheduled/Closed/Drafts/All with counts (Drafts added in PIPE-004), search, table (owner, title, department, status, candidates, to review, credits used/reserved, days remaining), sort needing-attention first, pagination (5/10/25), row menus per status. | PipelinesV2 |
| FR-PIPE-09 | "Reports" generates a PDF of all pipelines for the selected range (summaries, funnel, sources, drop-off reasons, credit usage) with a progress modal and download. | PipelinesV2 (G8) |
| FR-PIPE-10 | Share apply link: tiles for LinkedIn, JobStreet, Indeed, Kalibrr, Glassdoor, Facebook, Careers page, Other; clicking copies `…/apply/{workspace-slug}/{pipeline-slug}?source={id}` and shows the board-specific hint. | PipelinesV2, PipelineView |
| FR-PIPE-11 | Pipeline dashboard tab: KPIs, funnel, new applicants per day (14 days), interview score histogram with pass mark, sources (applicants, résumé pass rate), didn't-finish reasons with "Re-invite all" (new links for expired/unfinished candidates; confirmation first). | PipelineView (G1, G8) |
| FR-PIPE-12 | Candidates tab: stage filters with counts (All, Processing résumé, Résumé not a match, Invited, In progress, Ready for review, Didn't pass, Flagged, **Review requested**, **Advanced**, **Rejected**), search, table (candidate, stage, fit with explanation tooltip, source, applied), pagination (10/25/50). | PipelineView, ADR-015/017 |
| FR-PIPE-13 | Candidate row actions: view profile, download résumé, download candidate report (if interviewed), review flag (if flagged), email candidate (mailto), **advance** (ready/flagged-resolved), reject (reason required, team-only; optional email). | PipelineView, ADR-017 |
| FR-PIPE-14 | Setup tab shows the locked setup read-only with "Duplicate as new pipeline". | PipelineView |
| FR-PIPE-15 | Apply-link slugs are unique per workspace, derived from the title, and never change after publish. | — |

## FR-APPLY — Public apply page
| ID | Requirement | Source |
|---|---|---|
| FR-APPLY-01 | Public page per pipeline shows employer branding, status banner (accepting · closes date / opens on / not taking applications / closed), title, meta chips, JD, "Also open to", how applying works, fairness note, role facts, company card. | Apply |
| FR-APPLY-02 | Applying requires Google or Microsoft sign-in (ADR-014). The page explains the sign-in and what data is used. | Apply |
| FR-APPLY-03 | Application form: résumé PDF (required, ≤10 MB, text-based), full name (required, prefilled), email (from provider, read-only), contact number with country code (required), current city (optional), LinkedIn/portfolio URL (optional), consent checkbox (required; versioned text including AI use, recording, human decision, review rights, privacy link). | Apply |
| FR-APPLY-04 | Submitting records the source tag, consent version and time; uses 1 credit from the pipeline reserve (ADR-010); moves to `processing_resume`; shows the success modal and then "Applied on {date}". | Apply |
| FR-APPLY-05 | One active application per candidate per pipeline. A second attempt shows the existing application status. | — |
| FR-APPLY-06 | If the pipeline is not live (scheduled, paused, out of credits, closed), the Apply button is disabled with the right message; submissions that race a state change are rejected without using a credit. | PipelinesV2 |
| FR-APPLY-07 | Candidates cannot see or change anything after submitting except withdrawing their application (post-MVP) — MVP shows status text only. | — |

## FR-SCREEN — Résumé screening
| ID | Requirement | Source |
|---|---|---|
| FR-SCREEN-01 | Extract text from the PDF; if no usable text, mark "Couldn't read résumé" for TA and do not auto-reject. | — |
| FR-SCREEN-02 | Redact name, photo, contact details, address, age/date of birth, gender, graduation years and school names before any scoring (G2). | CandidateProfile |
| FR-SCREEN-03 | Score the résumé: must-haves (related/transferable evidence counts), nice-to-haves, relevant experience vs seniority, skill depth; weights 40/20/25/15; record verbatim evidence quotes, impact statements, claims to verify in interview, experience timeline. | CandidateProfile, ADR-013 |
| FR-SCREEN-04 | Apply "Also open to" rules (e.g. fresh graduates: projects count as experience; returning to work: gaps never penalised). | NewPipeline |
| FR-SCREEN-05 | Pass = score ≥ pass bar and all must-haves evidenced. Pass → generate interview plan, create interview link, send invitation. Fail → `resume_not_match`, schedule rejection email if enabled. Log to `ai_decisions`. | ADR-015 |
| FR-SCREEN-06 | Target: screening finishes within 2 minutes of applying (p95 < 5 min). | Overview |

## FR-INTV — AI interview (candidate)
| ID | Requirement | Source |
|---|---|---|
| FR-INTV-01 | Generate a personal interview plan from JD, redacted résumé, skills to probe, seniority, tone and "Also open to": ordered topics, résumé-anchored question seeds with source quotes, claims to verify. | Demo, CandidateProfile |
| FR-INTV-02 | Interview link page handles states: valid (welcome), not signed in (sign in with the account used to apply), wrong account, expired, already completed, pipeline cancelled, resume available. | Spec S-01, S-02 |
| FR-INTV-03 | Device check: camera (video format) with face-in-frame and wave detection; microphone read-aloud with level meter; clear fixes for blocked permissions. Consent checkbox (AI interviewer, recording, sharing with the employer, biometric face check when enabled). Start enabled only when checks pass and consent is given. | DemoDeviceCheck (G1, G7) |
| FR-INTV-04 | Live interview over OpenAI Realtime: AI speaks first, asks adaptive questions with follow-ups, answers the candidate's questions about the role (from the JD and company profile only), shows live captions, current topic, "From your résumé" source quote, mute, end interview, time remaining (30-min cap, wrap-up at 25). | DemoInterview, ADR-012 |
| FR-INTV-05 | Record candidate video (video format) and the mixed audio of both sides; upload in chunks during the session so a crash loses at most ~10 s. | CandidateProfile |
| FR-INTV-06 | Leaving mid-interview keeps progress; the candidate can resume while the link is valid; total talk time still capped at 30 min. | EmailTemplates (G1) |
| FR-INTV-07 | End screen thanks the candidate, explains next steps, and collects an optional 1–5 rating + comment that is not shared with the employer. | DemoInterview |
| FR-INTV-08 | Record drop-off reason codes: link expired, left mid-interview, technical issue. | Overview (G1) |
| FR-INTV-09 | Interview UI works with keyboard and screen readers; captions for every spoken question; works on current Chrome, Edge, Safari, Firefox desktop and mobile Safari/Chrome. | DS accessibility |

## FR-ASMT — Assessment
| ID | Requirement | Source |
|---|---|---|
| FR-ASMT-01 | Produce an authoritative timestamped, speaker-separated transcript from the recording. | CandidateProfile |
| FR-ASMT-02 | Score Technical fit, Communication and Culture alignment (0–100) from job-related evidence only; overall = weighted sum, rounded; show the calculation. | CandidateProfile (G4) |
| FR-ASMT-03 | For each criterion: sub-signals with scores, 2–4 evidence quotes with timestamps or résumé references, and "what held it back". | CandidateProfile |
| FR-ASMT-04 | Also produce: topic list with start times and topic scores, summary with numbered references, strengths, "worth probing next round", résumé claims confirmed in the interview, answer patterns (avg answer length, response delay, follow-ups, questions asked, talk time). | CandidateProfile |
| FR-ASMT-05 | Stage: ≥ pass mark → `ready_for_review`; below → `did_not_pass`. Fit badge per ADR-011. Log to `ai_decisions`. | ADR-011, 015 |
| FR-ASMT-06 | Run integrity checks when enabled (ADR-016); create flags with type, timestamps, detail; flagged candidates show under Flagged until every flag is resolved (No concern / Concern confirmed + note). | PipelineView (G7) |
| FR-ASMT-07 | Candidate profile Overview, Résumé and AI interview tabs as in the frame, including rank, pipeline average, distribution and comparisons (computed among completed interviews in the same pipeline). | CandidateProfile |
| FR-ASMT-08 | Candidate report PDF (résumé analysis, interview highlights, rubric scores, summary and evidence) with progress modal; résumé download of the original PDF. | PipelineView |
| FR-ASMT-09 | Target: assessment ready within 10 min of interview end (p95 < 20 min). | — |

## FR-CAND — Candidates pool
| ID | Requirement | Source |
|---|---|---|
| FR-CAND-01 | Read-only workspace-wide list of candidates within the member's scope: filters (all, applied more than once, interviewed, passed), search by name/email/skill, table, pagination. | CandidatePool |
| FR-CAND-02 | Profile drawer: applications, interviews, best score, latest assessment summary, score over time, Ava summary, skills, application history with links into pipelines. | CandidatePool |
| FR-CAND-03 | Dashboard tab: KPIs, new candidates per month, applications per candidate, outcomes, best sources, common skills. | CandidatePool (G8) |
| FR-CAND-04 | A candidate is matched across applications by their identity-provider account (same Supabase user) within a workspace. | — |

## FR-AVA — Ask Ava
| ID | Requirement | Source |
|---|---|---|
| FR-AVA-01 | Ava answers questions about one pipeline (Pipeline → Ask Ava) or the whole workspace (Candidates → Ask Ava), limited to what the asking member can see. | PipelineView, CandidatePool |
| FR-AVA-02 | Answers can include text, a comparison table and bullet points, and always list the sources they're based on (links to reports, recordings at timestamps, résumé screens). | PipelineView |
| FR-AVA-03 | Ava refuses to compare, rank or filter on protected or personal attributes (age, gender, photo, address, religion, marital status, pregnancy, graduation year, ethnicity, nationality) and offers job-related alternatives. | PipelineView (G2) |
| FR-AVA-04 | Ava suggests; it never rejects, advances or changes anything. | PipelineView |
| FR-AVA-05 | Threads are saved per member; "New chat" starts a fresh thread. Suggested prompts on empty state. | PipelineView |

## FR-MSG — Candidate emails
| ID | Requirement | Source |
|---|---|---|
| FR-MSG-01 | Each workspace has default templates: Interview invitation, Interview reminder, Finish your interview, Moving to the next stage, Not moving forward — résumé, Not moving forward — interview, **Interview received**, **Role closed**, **Human review received**. | EmailTemplates, ADR-015/017 |
| FR-MSG-02 | Editor: subject, rich text (bold, italic, link, bulleted list), insert parameter, reset to default, save, send test to me (sample data), version history with view and restore. Admins and Recruiters can edit. | EditEmailTemplate |
| FR-MSG-03 | Parameters: `[Candidate.firstname]`, `[Candidate.lastname]`, `[Job.title]`, `[Company.name]`, `[Interview.link]`, `[Interview.expiry]`, plus `[Review.link]` (rejections only, required, auto-appended if removed). | EditEmailTemplate, ADR-015 |
| FR-MSG-04 | Emails use the company logo/banner, are sent as "{Company} via FastHyr", and respect business-day delays in the workspace time zone. | CompanyProfile |
| FR-MSG-05 | Scheduled emails are cancelled if the application's state changes before sending (e.g. rejection cancelled after an override). | — |
| FR-MSG-06 | Every email is logged with status (queued, sent, delivered, bounced, failed). | — |

## FR-BILL — Billing and credits
| ID | Requirement | Source |
|---|---|---|
| FR-BILL-01 | Plans Starter/Growth/Scale and extra-credit packs as in ADR-004; prices and credit amounts are configuration. | BillingInvoices |
| FR-BILL-02 | New workspaces get 20 trial credits expiring after 30 days. | ADR-004 |
| FR-BILL-03 | Credit batches (trial, plan, extra) with amount, remaining, added, expiry; consumption order: plan → trial → extra (earliest expiry first). | BillingInvoices, CreditUsage |
| FR-BILL-04 | Pipeline reserves: reserving checks free credits; each application uses 1 reserved credit; reserve exhausted → pipeline pauses; unused reserve returns on close/cancel; top-up (+25/50/100/200) from free credits. If the workspace balance hits 0, live pipelines pause even with reserve left. | CreditUsage, NewPipeline |
| FR-BILL-05 | Billing page: plan card (name, price, credits, renewal, card), credits card, expiry table, payment method, billing details (company, billing email, address, tax ID), invoices list with detail and PDF. | BillingInvoices |
| FR-BILL-06 | Subscribe (first time), change plan (upgrade now with proration + credit top-up; downgrade at renewal), manage subscription and card via Stripe Customer Portal. | BillingInvoices |
| FR-BILL-07 | Buy extra credits with the saved card; confirmation shows credits added, expiry, receipt number. | BillingInvoices |
| FR-BILL-08 | Credit usage page: KPIs, reserved/free split, monthly plan vs extra usage, usage by department, alerts, per-pipeline table with outlook and top-up, ledger with pagination. | CreditUsage |
| FR-BILL-09 | Failed renewal payments: show "Payment failed" with Pay now; plan credits aren't granted until paid; existing batches keep working. | BillingInvoices |
| FR-BILL-10 | Only Admins see Billing & invoices and buy/change plans; Recruiters can top up pipelines in their departments from free credits; everyone sees credit status on their pipelines. | ADR-005 |

## FR-WEB — Public website
| ID | Requirement | Source |
|---|---|---|
| FR-WEB-01 | Main landing, TA landing and For-candidates pages as designed, with copy fixes from ADR-010/012/018 (no job listings, no "6–10 questions", "Find Jobs" → "For candidates"). | Main, TalentAcquisition, Candidates |
| FR-WEB-02 | Contact form (name, work email, company, message) stores the request, emails hello@fasthyr.com, is rate-limited and spam-protected. | TalentAcquisition |
| FR-WEB-03 | Pricing page with plans, packs and trial. | Spec S-07 |
| FR-WEB-04 | Terms of Service and Privacy Policy pages (content from counsel), plus an "AI in hiring" notice page linked from apply and interview screens. | Spec S-08 |

## FR-DEMO — Public demo
| ID | Requirement | Source |
|---|---|---|
| FR-DEMO-01 | 3-step setup: JD template or paste; résumé upload (PDF ≤10 MB) or sample; interviewer settings identical to the wizard (format, tone, seniority, focus areas from JD). | Demo, ADR-012 |
| FR-DEMO-02 | Device check and a real Realtime interview capped at 10 minutes; end screen with rating; CTAs to sign up. | DemoDeviceCheck, DemoInterview |
| FR-DEMO-03 | Demo data is never linked to a workspace, is not recorded to storage, and is deleted when the session ends (hard delete within 24 h). | Demo |
| FR-DEMO-04 | Abuse protection: rate limits per IP and per day, bot protection, global daily spend cap. | — |

## FR-COMP — Compliance
| ID | Requirement | Source |
|---|---|---|
| FR-COMP-01 | Versioned candidate notices and consent (apply, device check), stored per application/interview. | ADR-015/016 |
| FR-COMP-02 | Append-only `ai_decisions` log for résumé pass/fail, interview pass/fail, integrity flags. | ADR-015 |
| FR-COMP-03 | Human review request flow (candidate link → TA resolve → emails). | ADR-015 |
| FR-COMP-04 | Audit log for member, pipeline, billing, candidate-status and data-deletion actions. | — |
| FR-COMP-05 | Retention: default purge of candidate data 24 months after the candidate's last activity and recordings 12 months after the interview (workspace-configurable later); deletion of a candidate on request by an Admin within 30 days, including recordings, résumé, transcripts and derived data (keeping only a minimal deletion record). | `compliance/PRIVACY.md` |
| FR-COMP-06 | Bias monitoring: monthly report of pass rates by source and by optional self-reported demographics (post-MVP collection), and score parity checks in evaluation sets. | `compliance/BIAS_FAIRNESS.md` |

---

## Non-functional requirements
| ID | Requirement |
|---|---|
| NFR-01 | **Tenancy:** no API endpoint returns data from another workspace; enforced in the repository layer and covered by automated tests on every endpoint. |
| NFR-02 | **Security:** OWASP ASVS L2 practices; secrets only in environment variables; signed URLs expire ≤ 15 min; PDFs sanitised; rate limits on public endpoints. |
| NFR-03 | **Privacy:** no personal data in URLs, logs or analytics events (use IDs); PII redacted before AI scoring. |
| NFR-04 | **Performance:** TA pages interactive < 2.5 s (p75) on broadband; API p95 < 400 ms for reads; Realtime first response < 1.5 s. |
| NFR-05 | **Availability:** 99.5% monthly for API and web; background jobs retried with backoff; no lost applications. |
| NFR-06 | **Accessibility:** WCAG 2.2 AA on all screens; candidate interview fully usable by keyboard and screen reader. |
| NFR-07 | **Responsive, mobile first:** every page (marketing, candidate and TA app) is built mobile first and works from 360 px phones to 1440 px+ desktops with no horizontal page scroll, following `design/RESPONSIVE.md` (ADR-020). |
| NFR-08 | **Observability:** errors to Sentry with request IDs; AI calls logged with model, prompt version, tokens, latency, cost. |
| NFR-09 | **Cost control:** per-interview and per-workspace AI cost tracked; demo daily spend cap. |
| NFR-10 | **Data protection:** encrypted at rest and in transit; daily backups with point-in-time recovery on production. |
| NFR-11 | **Browser support:** last two versions of Chrome, Edge, Safari, Firefox. |
| NFR-12 | **Internationalisation readiness:** all UI copy in message files; dates, times and currency formatted per locale and workspace time zone. |

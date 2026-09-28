# Roadmap

MVP = everything in the design canvas, adjusted by ADR-010 to ADR-018. Work is split into milestones that each end in something demoable. Task status lives in [`../tasks/BOARD.md`](../tasks/BOARD.md).

## MVP milestones

| Milestone | Goal (demo at the end) | Epics |
|---|---|---|
| **M0 Foundation** | Monorepo builds, deploys to the development environment, CI green, UI kit, AI/email/storage layers in place | FND-001..014 |
| **M1 Access** | Sign in, create/join workspace (with trial credits), switch, admin screens for profile, departments, members | AUTH, WS, DASH-001, BILL-002 |
| **M2 Pipelines** | Create, publish, list and manage pipelines with credit reserves (trial credits only) | PIPE-001..006, BILL-001 |
| **M3 Intake** | Candidate applies through a tagged link, résumé screened, interview planned, invited or rejected by email | APPLY, SCREEN-001..003, INTV-001, MSG, COMP-002 |
| **M4 AI interview** | Invited candidate completes a real video/voice AI interview with recording and transcript | INTV-002..009 |
| **M5 Review** | Scored, explainable assessments; candidate profile; advance/reject; flags; human review; Ava; candidate pool; pipeline dashboards | ASMT, PIPE-007..010, DASH-003, SCREEN-004, CAND-001, AVA |
| **M6 Billing & analytics** | Paid plans, packs, invoices, credit usage, Overview and Getting started | BILL-003..006, DASH-002, DASH-004, CAND-002 |
| **M7 Public site & demo** | Marketing pages, pricing, legal pages, public demo | WEB, INTV-010 |
| **M8 Launch readiness** | Compliance jobs, e2e tests, security review, production cut-over | COMP-001, COMP-003, COMP-004, REL |

M6 and M7 can run in parallel with M5 once M4 is done.

## Post-MVP backlog (not scheduled)
- Multi-stage pipelines inside FastHyr and human-interview scheduling (G6, G9).
- Public job board ("Find Jobs").
- Candidate email magic-link sign-in (revisit ADR-014 based on drop-off data).
- Multi-language interviews.
- Question performance analytics (which topics differentiate candidates) (G8).
- In-app notifications and digest emails for TA users.
- Custom rubric criteria.
- Enterprise SSO/SAML, audit exports, data residency regions.
- Self-reported demographic collection for bias audits (opt-in).
- Candidate self-service (withdraw application, download my data).

## Open questions (decide before launch)
| # | Question | Owner |
|---|---|---|
| OQ-1 | Tax on invoices: enable Stripe Tax (VAT/GST/US sales tax) for global customers? | Product + accountant |
| OQ-2 | Legal entity, address and tax ID printed on invoices ("[FastHyr legal address]" in design). | Product |
| OQ-3 | Terms of Service, Privacy Policy, AI-in-hiring notice, DPA text — reviewed by counsel. | Product + counsel |
| OQ-4 | Launch jurisdictions: do we accept pipelines for NYC-based roles (requires an independent bias audit first) and EU roles (AI Act obligations)? | Product + counsel |
| OQ-5 | Supabase region for production (latency vs data residency expectations of first customers). | Tech lead |
| OQ-6 | Welcome video and tutorials content for Getting started. | Product |
| OQ-7 | Trial size (20 credits / 30 days) and plan prices — confirm before launch. | Product |

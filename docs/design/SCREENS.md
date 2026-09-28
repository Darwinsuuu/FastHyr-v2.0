# Screen inventory

Every MVP screen: where its design is, its route (`architecture/FRONTEND.md`), and the tasks that build it. "Frame" = canvas file `project/<Frame>.dc.html`; "S-xx"/"A-xx" = `SCREEN_SPECS.md`.

## Public site (`fasthyr.com`)
| Screen | Design | Route | Tasks |
|---|---|---|---|
| Main landing | Frame `Main` | `/` | WEB-001 |
| Talent acquisition landing + contact form | Frame `TalentAcquisition` | `/employers` | WEB-002 |
| For candidates (marketing only) | Frame `Candidates` + A-10 | `/candidates` | WEB-003 |
| Pricing | S-07 | `/pricing` | WEB-004 |
| Terms, Privacy, AI in hiring | S-08 | `/terms`, `/privacy`, `/ai-in-hiring` | WEB-005 |
| Demo setup | Frame `Demo` + A-09 | `/demo` | INTV-010 |
| Demo camera & mic check | Frame `DemoDeviceCheck` | `/demo/check` | INTV-010 (reuses INTV-003) |
| Demo AI interview | Frame `DemoInterview` | `/demo/interview` | INTV-010 (reuses INTV-005) |

## Candidate flow
| Screen | Design | Route | Tasks |
|---|---|---|---|
| Apply page, sign-in modal, application form, sent modal | Frame `Apply` | `/apply/[ws]/[pipeline]` | APPLY-001..004 |
| Interview link landing + states (welcome, sign in, wrong account, expired, completed, unavailable, resume) | S-01 | `/interview/[token]` | INTV-002 |
| Device check + consent | Frame `DemoDeviceCheck` (+ biometric consent line, S-01) | `/interview/[token]` step | INTV-003 |
| Live interview | Frame `DemoInterview` | `/interview/[token]` step | INTV-005 |
| End screen + feedback | Frame `DemoInterview` (done state) + S-02 | `/interview/[token]` step | INTV-009 |
| Human review request | S-03 | `/review-request/[token]` | ASMT-008 |

## Employer sign-in
| Screen | Design | Route | Tasks |
|---|---|---|---|
| Employer login + forgot password modal | Frame `EmployerLogin` | `/login` | AUTH-001, AUTH-002 |
| Set a new password | S-05 | `/reset-password` | AUTH-002 |
| Verify your email | S-06 | `/verify-email` | AUTH-002 |
| Choose workspace + user profile modal | Frame `WorkspaceSelect` | `/workspaces` | AUTH-003, AUTH-005 |
| Join a workspace (from invite) | S-04 | `/join/[code]` | AUTH-004 |

## TA app (`app.fasthyr.com`)
| Screen | Design | Route | Tasks |
|---|---|---|---|
| App shell (sidebar, workspace switcher, user menu) | All app frames | layout | DASH-001 |
| Getting started | Frame `GettingStarted` + A-08 | `/getting-started` | DASH-002 |
| Overview | Frame `Overview` + A-03 | `/overview` | DASH-003, DASH-004 |
| Pipelines list + modals | Frame `PipelinesV2` | `/pipelines` | PIPE-004, PIPE-005, PIPE-006, PIPE-010 |
| New pipeline wizard | Frame `NewPipeline` + A-01 | `/pipelines/new`, `/pipelines/[id]/edit` | PIPE-002, PIPE-003 |
| Pipeline details — Dashboard | Frame `PipelineView` | `/pipelines/[id]?tab=dashboard` | PIPE-007 |
| Pipeline details — Candidates | Frame `PipelineView` + A-02, A-03 | `?tab=candidates` | PIPE-008, ASMT-007 |
| Pipeline details — Ask Ava | Frame `PipelineView` | `?tab=ava` | AVA-002 |
| Pipeline details — Setup | Frame `PipelineView` | `?tab=setup` | PIPE-009 |
| Candidates pool (dashboard, list, drawer, Ava) | Frame `CandidatePool` + A-05 | `/candidates` | CAND-001, CAND-002, AVA-002, COMP-003 |
| Candidate profile (overview, résumé, interview) | Frame `CandidateProfile` + A-02, A-03, A-04 | `/candidates/[id]?application=` | ASMT-003..009 |
| Billing & invoices + buy credits + change plan | Frame `BillingInvoices` + A-06 | `/billing` | BILL-003, BILL-004, BILL-005 |
| Credit usage + top-up | Frame `CreditUsage` | `/billing/usage` | BILL-006 |
| Company profile | Frame `CompanyProfile` | `/settings/company` | WS-001 |
| Departments | Frame `Departments` | `/settings/departments` | WS-002 |
| Manage members + invites | Frame `ManageMembers` | `/settings/members` | WS-003, WS-004 |
| Email templates list | Frame `EmailTemplates` + A-07 | `/settings/email-templates` | MSG-002 |
| Edit email template | Frame `EditEmailTemplate` | `/settings/email-templates/[key]` | MSG-002 |

## Shared patterns (appear in many frames)
- Report / download progress dialog ("Please don't close or refresh this window") → `JobProgressDialog` (FND-012), used by PIPE-010, ASMT-009, BILL-003.
- Share apply link modal → PIPE-006 (used in Pipelines list, wizard done step, pipeline header).
- Account modal (user profile) → AUTH-005.

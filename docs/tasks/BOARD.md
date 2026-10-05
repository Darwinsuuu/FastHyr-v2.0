# Task board

Single source of truth for task status. Update the **Status** column in the same PR that changes a task's state (see [`process/DEV_WORKFLOW.md`](../process/DEV_WORKFLOW.md)).

Statuses: `Backlog` · `Ready` · `In progress` · `In review` · `Blocked` · `Done`. A task is `Ready` when all its dependencies are `Done`.

**90 tasks** across 9 milestones. Milestone goals are in [`product/ROADMAP.md`](../product/ROADMAP.md).

## Summary

| Milestone | Tasks | Done |
|---|---|---|
| M0 Foundation | 14 | 14 |
| M1 Access | 12 | 11 |
| M2 Pipelines | 7 | 3 |
| M3 Intake | 12 | 11 |
| M4 AI interview | 8 | 3 |
| M5 Review | 18 | 0 |
| M6 Billing & analytics | 7 | 0 |
| M7 Public site & demo | 6 | 0 |
| M8 Launch readiness | 6 | 0 |

## M0 Foundation

| ID | Task | Size | Depends on | Status | PR |
|---|---|---|---|---|---|
| [FND-001](FND/FND-001-monorepo-scaffold.md) | Monorepo scaffold | M | — | Done | #2 |
| [FND-002](FND/FND-002-supabase-local-setup-and-environments.md) | Supabase local setup and environments | S | FND-001 | Done | #3 |
| [FND-003](FND/FND-003-core-schema-identity-workspaces-members-department.md) | Core schema: identity, workspaces, members, departments, invites | M | FND-002 | Done | #4 |
| [FND-004](FND/FND-004-api-skeleton-auth-request-context-permissions-erro.md) | API skeleton: auth, request context, permissions, errors | M | FND-003 | Done | #5 |
| [FND-005](FND/FND-005-web-skeleton-hosts-tokens-fonts-auth-session-api-c.md) | Web skeleton: hosts, tokens, fonts, auth session, API client | M | FND-004 | Done | #6 |
| [FND-006](FND/FND-006-ci-pipeline.md) | CI pipeline | S | FND-005 | Done | #11 |
| [FND-007](FND/FND-007-deployments-vercel-render-blueprint-dev-and-qa-env.md) | Deployments: Vercel, Render blueprint, dev and QA environments | M | FND-006, FND-008 | Done | #26 |
| [FND-008](FND/FND-008-background-worker-and-job-framework.md) | Background worker and job framework | M | FND-004 | Done | #20 |
| [FND-009](FND/FND-009-observability-sentry-structured-logs.md) | Observability: Sentry, structured logs | S | FND-005, FND-008 | Done | #25 |
| [FND-010](FND/FND-010-email-infrastructure-resend.md) | Email infrastructure (Resend) | M | FND-008 | Done | #22 |
| [FND-011](FND/FND-011-storage-service-and-pdf-handling.md) | Storage service and PDF handling | M | FND-004 | Done | #24 |
| [FND-012](FND/FND-012-ui-kit-design-system-components.md) | UI kit (design-system components) | L | FND-005 | Done | #7, #8 |
| [FND-013](FND/FND-013-openai-integration-layer.md) | OpenAI integration layer | M | FND-004 | Done | #21 |
| [FND-014](FND/FND-014-seed-data-acme-talent-sample-workspace.md) | Seed data: Acme Talent sample workspace | S | FND-003 | Done | #23 |

## M1 Access

| ID | Task | Size | Depends on | Status | PR |
|---|---|---|---|---|---|
| [AUTH-001](AUTH/AUTH-001-employer-sign-in.md) | Employer sign-in | M | FND-005, FND-012 | Done | #9 |
| [AUTH-002](AUTH/AUTH-002-password-reset-and-email-verification.md) | Password reset and email verification | S | AUTH-001, FND-010 | Done | #10 |
| [AUTH-003](AUTH/AUTH-003-workspaces-create-join-by-code-select-switch.md) | Workspaces: create, join by code, select, switch | M | AUTH-001, FND-003, BILL-002 | Done | #12 |
| [AUTH-004](AUTH/AUTH-004-invite-accept-page.md) | Invite accept page | S | WS-004 | Done | #19 |
| [AUTH-005](AUTH/AUTH-005-user-profile-modal-and-account-menu.md) | User profile modal and account menu | S | DASH-001 | Done | #18 |
| [WS-001](WS/WS-001-company-profile.md) | Company profile | M | DASH-001, FND-011 | Done | #30 |
| [WS-002](WS/WS-002-departments.md) | Departments | S | DASH-001 | Done | #15 |
| [WS-003](WS/WS-003-manage-members.md) | Manage members | M | WS-002 | Done | #16 |
| [WS-004](WS/WS-004-member-invites.md) | Member invites | M | WS-003, FND-010 | Done | #17 |
| [WS-005](WS/WS-005-permission-matrix-and-department-scoping-end-to-en.md) | Permission matrix and department scoping end to end | M | WS-003 | Ready | |
| [DASH-001](DASH/DASH-001-app-shell.md) | App shell | M | FND-012, AUTH-003 | Done | #14 |
| [BILL-002](BILL/BILL-002-credit-ledger-service.md) | Credit ledger service | L | FND-003 | Done | #13 |

## M2 Pipelines

| ID | Task | Size | Depends on | Status | PR |
|---|---|---|---|---|---|
| [PIPE-001](PIPE/PIPE-001-pipeline-model-and-state-machine.md) | Pipeline model and state machine | M | FND-003, FND-008, BILL-002 | Done | #27 |
| [PIPE-002](PIPE/PIPE-002-new-pipeline-wizard-role-and-ai-interview-steps.md) | New pipeline wizard — Role and AI interview steps | L | PIPE-001, WS-002, FND-012 | Done | #28 |
| [PIPE-003](PIPE/PIPE-003-new-pipeline-wizard-scoring-schedule-credits-revie.md) | New pipeline wizard — Scoring, Schedule & credits, Review, Publish | L | PIPE-002 | Done | #29 |
| [PIPE-004](PIPE/PIPE-004-pipelines-list.md) | Pipelines list | M | PIPE-001, DASH-001 | Ready | |
| [PIPE-005](PIPE/PIPE-005-pipeline-lifecycle-actions.md) | Pipeline lifecycle actions | M | PIPE-004, FND-010 | Backlog | |
| [PIPE-006](PIPE/PIPE-006-share-apply-link.md) | Share apply link | S | PIPE-001 | Ready | |
| [BILL-001](BILL/BILL-001-stripe-foundation-and-webhooks.md) | Stripe foundation and webhooks | M | FND-004, FND-008 | Ready | |

## M3 Intake

| ID | Task | Size | Depends on | Status | PR |
|---|---|---|---|---|---|
| [APPLY-001](APPLY/APPLY-001-public-apply-page.md) | Public apply page | M | PIPE-001, WS-001, FND-012 | Done | |
| [APPLY-002](APPLY/APPLY-002-candidate-sign-in-on-the-apply-page.md) | Candidate sign-in on the apply page | S | APPLY-001, AUTH-001 | Done | |
| [APPLY-003](APPLY/APPLY-003-application-submission-and-credit-use.md) | Application submission and credit use | L | APPLY-002, FND-011, BILL-002, COMP-002 | Done | |
| [APPLY-004](APPLY/APPLY-004-apply-edge-cases-and-states.md) | Apply edge cases and states | S | APPLY-003 | Done | |
| [SCREEN-001](SCREEN/SCREEN-001-resume-text-extraction-and-pii-redaction.md) | Résumé text extraction and PII redaction | M | FND-011, FND-013 | Done | #36 |
| [SCREEN-002](SCREEN/SCREEN-002-resume-assessment-and-decision.md) | Résumé assessment and decision | L | SCREEN-001, PIPE-001 | Done | #37 |
| [SCREEN-003](SCREEN/SCREEN-003-post-screen-actions-invite-or-schedule-rejection.md) | Post-screen actions: invite or schedule rejection | M | SCREEN-002, MSG-003, INTV-001 | Done | #41 |
| [INTV-001](INTV/INTV-001-interview-plan-generation.md) | Interview plan generation | M | SCREEN-002 | Done | #38 |
| [MSG-001](MSG/MSG-001-email-templates-model-and-defaults.md) | Email templates model and defaults | M | FND-010, AUTH-003 | Done | #39 |
| [MSG-002](MSG/MSG-002-email-templates-list-and-editor.md) | Email templates list and editor | M | MSG-001, DASH-001 | Ready | |
| [MSG-003](MSG/MSG-003-email-scheduling-and-sending-engine.md) | Email scheduling and sending engine | M | MSG-001, FND-008 | Done | |
| [COMP-002](COMP/COMP-002-notices-and-consent-versioning.md) | Notices and consent versioning | S | FND-004 | Done | |

## M4 AI interview

| ID | Task | Size | Depends on | Status | PR |
|---|---|---|---|---|---|
| [INTV-002](INTV/INTV-002-interview-link-page-and-states.md) | Interview link page and states | M | SCREEN-003, APPLY-002 | Done | #42 |
| [INTV-003](INTV/INTV-003-device-check-and-consent.md) | Device check and consent | M | INTV-002, COMP-002 | Done | #43 |
| [INTV-004](INTV/INTV-004-realtime-session-service-server.md) | Realtime session service (server) | L | INTV-001, INTV-002, FND-013 | Done | #44 |
| [INTV-005](INTV/INTV-005-live-interview-ui-client.md) | Live interview UI (client) | L | INTV-003, INTV-004 | Done | |
| [INTV-006](INTV/INTV-006-recording-capture-and-finalisation.md) | Recording capture and finalisation | L | INTV-005, FND-011 | Ready | |
| [INTV-007](INTV/INTV-007-interview-lifecycle-resume-expiry-reminders-re-inv.md) | Interview lifecycle: resume, expiry, reminders, re-invite, drop-off reasons | M | INTV-005, MSG-003 | Ready | |
| [INTV-008](INTV/INTV-008-authoritative-transcription.md) | Authoritative transcription | M | INTV-006 | Backlog | |
| [INTV-009](INTV/INTV-009-interview-end-screen-and-feedback.md) | Interview end screen and feedback | S | INTV-006 | Backlog | |

## M5 Review

| ID | Task | Size | Depends on | Status | PR |
|---|---|---|---|---|---|
| [DASH-003](DASH/DASH-003-analytics-views-and-endpoints.md) | Analytics views and endpoints | M | PIPE-001, APPLY-003, INTV-007, ASMT-001 | Backlog | |
| [PIPE-007](PIPE/PIPE-007-pipeline-details-header-and-dashboard-tab.md) | Pipeline details — header and Dashboard tab | M | DASH-003, PIPE-004 | Backlog | |
| [PIPE-008](PIPE/PIPE-008-pipeline-details-candidates-tab.md) | Pipeline details — Candidates tab | M | PIPE-007, APPLY-003 | Backlog | |
| [PIPE-009](PIPE/PIPE-009-pipeline-details-setup-tab-and-duplicate.md) | Pipeline details — Setup tab and duplicate | S | PIPE-007 | Backlog | |
| [PIPE-010](PIPE/PIPE-010-pipelines-report-pdf.md) | Pipelines report PDF | M | DASH-003, FND-008 | Backlog | |
| [SCREEN-004](SCREEN/SCREEN-004-unreadable-resumes-and-manual-invite.md) | Unreadable résumés and manual invite | S | SCREEN-003, PIPE-008 | Backlog | |
| [ASMT-001](ASMT/ASMT-001-interview-scoring.md) | Interview scoring | L | INTV-008, FND-013 | Backlog | |
| [ASMT-002](ASMT/ASMT-002-integrity-checks-worker.md) | Integrity checks (worker) | L | INTV-008 | Backlog | |
| [ASMT-003](ASMT/ASMT-003-flag-review-ui.md) | Flag review UI | S | ASMT-002, ASMT-004 | Backlog | |
| [ASMT-004](ASMT/ASMT-004-candidate-profile-header-and-overview-tab.md) | Candidate profile — header and Overview tab | L | ASMT-001, PIPE-008 | Backlog | |
| [ASMT-005](ASMT/ASMT-005-candidate-profile-resume-tab.md) | Candidate profile — Résumé tab | M | ASMT-004, SCREEN-002 | Backlog | |
| [ASMT-006](ASMT/ASMT-006-candidate-profile-ai-interview-tab.md) | Candidate profile — AI interview tab | M | ASMT-004, INTV-008 | Backlog | |
| [ASMT-007](ASMT/ASMT-007-advance-and-reject-actions.md) | Advance and reject actions | M | PIPE-008, MSG-003 | Backlog | |
| [ASMT-008](ASMT/ASMT-008-human-review-requests.md) | Human review requests | M | ASMT-007, SCREEN-003 | Backlog | |
| [ASMT-009](ASMT/ASMT-009-candidate-report-pdf-and-resume-download.md) | Candidate report PDF and résumé download | M | ASMT-004, PIPE-010 | Backlog | |
| [CAND-001](CAND/CAND-001-candidates-pool-list-and-profile-drawer.md) | Candidates pool — list and profile drawer | M | ASMT-001, WS-005 | Backlog | |
| [AVA-001](AVA/AVA-001-ava-backend-scoped-assistant.md) | Ava backend (scoped assistant) | L | ASMT-001, WS-005, FND-013 | Backlog | |
| [AVA-002](AVA/AVA-002-ava-ui.md) | Ava UI | M | AVA-001, PIPE-007, CAND-001 | Backlog | |

## M6 Billing & analytics

| ID | Task | Size | Depends on | Status | PR |
|---|---|---|---|---|---|
| [DASH-002](DASH/DASH-002-getting-started.md) | Getting started | S | DASH-001, WS-001, WS-004, MSG-002, BILL-004, PIPE-003 | Backlog | |
| [DASH-004](DASH/DASH-004-overview-page.md) | Overview page | M | DASH-003, BILL-006, ASMT-008 | Backlog | |
| [CAND-002](CAND/CAND-002-candidates-pool-dashboard.md) | Candidates pool — dashboard | S | CAND-001, DASH-003 | Backlog | |
| [BILL-003](BILL/BILL-003-billing-invoices-page.md) | Billing & invoices page | M | BILL-001, BILL-002, DASH-001 | Backlog | |
| [BILL-004](BILL/BILL-004-subscribe-and-change-plan.md) | Subscribe and change plan | M | BILL-003 | Backlog | |
| [BILL-005](BILL/BILL-005-buy-extra-credits.md) | Buy extra credits | S | BILL-003 | Backlog | |
| [BILL-006](BILL/BILL-006-credit-usage-page-and-pipeline-top-up.md) | Credit usage page and pipeline top-up | M | BILL-002, PIPE-004, DASH-003 | Backlog | |

## M7 Public site & demo

| ID | Task | Size | Depends on | Status | PR |
|---|---|---|---|---|---|
| [INTV-010](INTV/INTV-010-public-demo.md) | Public demo | L | INTV-005, SCREEN-001 | Ready | |
| [WEB-001](WEB/WEB-001-main-landing-page.md) | Main landing page | M | FND-012 | Ready | |
| [WEB-002](WEB/WEB-002-talent-acquisition-landing-and-contact-form.md) | Talent acquisition landing and contact form | M | FND-012, FND-010 | Ready | |
| [WEB-003](WEB/WEB-003-for-candidates-page-marketing.md) | For candidates page (marketing) | S | FND-012 | Ready | |
| [WEB-004](WEB/WEB-004-pricing-page.md) | Pricing page | S | FND-012, BILL-001 | Backlog | |
| [WEB-005](WEB/WEB-005-legal-and-ai-in-hiring-pages.md) | Legal and AI-in-hiring pages | S | FND-012 | Ready | |

## M8 Launch readiness

| ID | Task | Size | Depends on | Status | PR |
|---|---|---|---|---|---|
| [COMP-001](COMP/COMP-001-ai-decision-log-and-audit-log-coverage.md) | AI decision log and audit log coverage | M | SCREEN-002, ASMT-001, ASMT-002 | Backlog | |
| [COMP-003](COMP/COMP-003-candidate-data-deletion-and-retention.md) | Candidate data deletion and retention | M | CAND-001, FND-011 | Backlog | |
| [COMP-004](COMP/COMP-004-bias-evaluation-suite.md) | Bias evaluation suite | M | SCREEN-002, ASMT-001, AVA-001 | Backlog | |
| [REL-001](REL/REL-001-end-to-end-test-suite.md) | End-to-end test suite | M | ASMT-007, BILL-005 | Backlog | |
| [REL-002](REL/REL-002-security-review.md) | Security review | M | REL-001 | Backlog | |
| [REL-003](REL/REL-003-production-launch-readiness.md) | Production launch readiness | M | REL-002, WEB-005, COMP-003 | Backlog | |

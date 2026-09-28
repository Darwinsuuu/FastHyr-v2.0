# Architecture & product decisions (ADRs)

Each decision gets one file: `ADR-NNN-short-slug.md`, using [`../process/templates/ADR_TEMPLATE.md`](../process/templates/ADR_TEMPLATE.md).
ADRs are append-only. To change a decision, write a new ADR that **supersedes** the old one and update the old one's status line.

| ADR | Decision | Status |
|---|---|---|
| [001](ADR-001-monorepo-nextjs-fastapi.md) | Monorepo: Next.js web app + FastAPI API + Python worker | Accepted |
| [002](ADR-002-supabase-auth-db-storage.md) | Supabase for Auth, Postgres and Storage | Accepted |
| [003](ADR-003-hosting-vercel-render.md) | Vercel for web, Render for API, worker and Redis | Accepted |
| [004](ADR-004-stripe-plans-and-credits.md) | Stripe: monthly plans, credit packs, trial credits | Accepted |
| [005](ADR-005-tenancy-and-roles.md) | Workspace tenancy, departments and three roles | Accepted |
| [006](ADR-006-data-access-path.md) | Browser talks to FastAPI only (plus Supabase Auth and signed storage URLs) | Accepted |
| [007](ADR-007-openai-for-all-ai.md) | OpenAI for all AI: Realtime API for interviews, text models for everything else | Accepted |
| [008](ADR-008-resend-for-email.md) | Resend for transactional email | Accepted |
| [009](ADR-009-background-jobs.md) | Background jobs with arq + Redis on a Render worker | Accepted |
| [010](ADR-010-credit-used-on-apply.md) | One credit is used when a candidate applies | Accepted |
| [011](ADR-011-numeric-explainable-scores.md) | Numeric, explainable scores on TA screens | Accepted |
| [012](ADR-012-interview-format-rules.md) | Adaptive interview, 30-minute cap, English only, wizard settings are canonical | Accepted |
| [013](ADR-013-resume-screening-rule.md) | Résumé pass bar and nice-to-haves are set per pipeline | Accepted |
| [014](ADR-014-candidate-sso-only.md) | Candidates sign in with Google or Microsoft only | Accepted |
| [015](ADR-015-automated-decisions-human-review.md) | Automated rejections stay, with a human-review offer and a decision log | Accepted |
| [016](ADR-016-integrity-checks-scope.md) | Integrity checks: same face, second voice, read-aloud, timing; flags never reject | Accepted |
| [017](ADR-017-manual-advance-action.md) | Manual "Advance" action sends the next-stage email | Accepted |
| [018](ADR-018-mvp-scope-clarifications.md) | MVP scope clarifications: job board, Ava, demo settings, missing screens, Claude builds | Accepted |
| [019](ADR-019-branching-environments-testing.md) | Branches master/release/develop ↔ production/QA/development; tests written after the feature works, important functional only | Accepted |
| [020](ADR-020-mobile-first-responsive.md) | Every page is responsive and built mobile first | Accepted |

# FND-014: Seed data: Acme Talent sample workspace

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | In review |
| Size | S |
| Depends on | [FND-003](../FND/FND-003-core-schema-identity-workspaces-members-department.md) |
| Requirements | — |
| Gap areas | — |
| Design | All frames (sample data) |
| Docs to read | [`architecture/DATABASE.md §5`](../../architecture/DATABASE.md), [`_sources/design-canvas-inventory.md`](../../_sources/design-canvas-inventory.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Local, development and QA databases contain the design's sample workspace so screens can be built against realistic data.

## Scope
**In:**
- `supabase/seed.sql` (and a Python seeder for later tables, extended by each epic)
- Acme Talent, departments, members, pipelines in each status

**Out:**
- —

## Acceptance criteria
- [x] `make db-reset` yields a workspace matching the design's sample numbers roughly
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Synthetic people only; extend the seeder as tables are added (each task updates it)

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
**Where:** a Python seeder, `apps/api/scripts/seed.py`, rather than `seed.sql`, so credits go through `app/services/credits.py` (batches, reserves and ledger add up exactly) and later epics extend it with their models. `supabase/seed.sql` keeps only the local API role password, so CI (which never runs the seeder) is unchanged.

**How it runs:** `make db-seed`; `make db-reset` and `make setup` call it. It connects as the database owner (`SEED_DATABASE_URL`, default local Supabase) because it writes `auth.users` and `auth.identities`. It does nothing when the `acme-talent` workspace exists. Against a non-local database it needs `SEED_USER_PASSWORD`.

**Data (from frames ManageMembers, Departments, PipelinesV2, CreditUsage, CompanyProfile):**
- Users (synthetic, `@acme-talent.test`, confirmed email + password): Dana Lim (Admin, owner; stands in for the frame's "(you)"), Maria Santos (Recruiter; Engineering, Design), Jomar Reyes (Hiring manager; Engineering), Angela Cruz (Recruiter; Customer Support), with the frame's last-active times.
- Pending invites: a Hiring manager sent 2 days ago and a Recruiter sent 5 days ago.
- Company profile, and the 9 departments with their descriptions and creation dates.
- 20 pipelines: the frame's 18 plus a draft and a manually paused one, so every status appears. Titles live in the seeder until PIPE-001 adds the column.
- Credits replayed through the service: the trial (expired), a credit pack, each pipeline's reserve and applicants, closed and cancelled reserves released, then this month's 300-credit plan and the 190 applicants it paid for. The result matches CreditUsage: 1,640 available (110 plan, 1,530 extra).

**Test:** `tests/unit/test_seed_data.py` keeps the sample data consistent (every status, used within reserve, departments exist, plan left 110).

## Log
- 2026-10-01: branch `feature/seed-data` from `develop`. Plan auto-approved (Darwin's standing rule: no plan approvals).
- Decision: the owner is a synthetic "Dana Lim" (same DL initials as the frame) instead of the frame's real name; all emails use the reserved `.test` domain.
- Decision: ledger rows all carry the seed time, since the ledger is append-only and the service stamps `created_at`; "used this month" style reports built later will count every seeded applicant as this month until they read applications instead.
- Hand test: `make db-reset` on a fresh database seeded in ~7 s; a second `make db-seed` skipped. Batches: plan 300/110 left, extra 2,497/1,530 left, trial expired. Signed in as dana, maria and jomar; Manage members, Pending invites and Departments show the sample data at 360, 768, 1024 and 1440 px (screenshots: project files `screenshots/FND-014/`). `make test-api` passes on the seeded database (180).

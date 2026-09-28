# FND-003: Core schema: identity, workspaces, members, departments, invites

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | Backlog |
| Size | M |
| Depends on | [FND-002](../FND/FND-002-supabase-local-setup-and-environments.md) |
| Requirements | FR-AUTH-05, FR-WS-02, FR-WS-03 |
| Gap areas | — |
| Design | — |
| Docs to read | [`architecture/DATABASE.md §2 (Identity and workspaces)`](../../architecture/DATABASE.md), [`architecture/MULTI_TENANCY.md`](../../architecture/MULTI_TENANCY.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
The first migration creates identity and tenancy tables with RLS locked down, and SQLAlchemy models mirror them.

## Scope
**In:**
- Migrations: profiles, workspaces, company_profiles, departments, workspace_members, member_departments, invites, audit_log
- RLS enabled on every table, no policies for anon/authenticated; dedicated API DB role with grants
- Trigger: create `profiles` row on `auth.users` insert
- SQLAlchemy models + drift check script used by CI

**Out:**
- Pipeline and later tables (added by their tasks)

## Acceptance criteria
- [ ] `make db-reset` applies migrations cleanly
- [ ] Anon key cannot select from any table (test)
- [ ] Composite FKs `(workspace_id, id)` used between tenant tables
- [ ] Model/migration drift check passes
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- UUID v7 generated in API; DB default `gen_random_uuid()` only as fallback

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Integration test with the anon key proving RLS denial

## Implementation plan
Branch: `feature/core-schema-ho4ypt` from `develop`.

**Migration** `supabase/migrations/<timestamp>_core_schema.sql` (SQL is the source of truth; no Alembic migrations):
- Tables exactly as `DATABASE.md` §2 "Identity and workspaces": `profiles`, `workspaces`, `company_profiles`, `departments`, `workspace_members`, `member_departments`, `invites`, plus `audit_log` from §2 "Compliance and ops".
- `id uuid primary key default gen_random_uuid()` (the API sends UUID v7; the default is only a fallback). Enums as `text` + `check`. All times `timestamptz`.
- **Tenancy:** every tenant table has `workspace_id not null`; parents (`departments`, `workspace_members`) get `unique (workspace_id, id)` so children use composite FKs: `member_departments (workspace_id, member_id)` and `(workspace_id, department_id)`. `company_profiles`, `invites` and `audit_log` reference `workspaces(id)`.
- **Rules in the database:** department names unique per workspace ignoring case, and "No department" rejected; one member row per `(workspace_id, user_id)`; one owner per workspace, and the owner must be an Admin; invite `code` and `token_hash` unique, and at most one pending invite per email per workspace (resend rotates the token on the same row); `company_profiles.about` ≤ 600 characters.
- **Deletes:** restrictive by default. Removing a member or deleting a department cascades to `member_departments` (FR-WS-02). `invites.department_ids` is an array, so the department service removes a deleted ID from pending invites (noted for WS tasks).
- People columns (`owner_id`, `invited_by`, `accepted_by`, `updated_by`) reference `profiles(id)`. `audit_log.actor_id` has no FK so the log never changes when a user is deleted.
- **audit_log is append-only:** the API role gets only `select, insert`, and a trigger rejects `update`/`delete` for everyone.
- **New-user trigger:** on `auth.users` insert, create the `profiles` row, taking `full_name` and `avatar_url` from the Google/Microsoft metadata when present (`security definer`, empty `search_path`, not callable by `anon`/`authenticated`).
- Indexes: `workspace_members (user_id)` for "my workspaces", `audit_log (workspace_id, created_at)`, plus the unique ones above.

**Locking it down (ADR-006):**
- RLS enabled on every table with **no** policies.
- Revoke all table and function privileges from `anon` and `authenticated`, and change Supabase's default privileges so tables added by later migrations are not granted to them either.
- New role `fasthyr_api` (NOLOGIN in the migration, `BYPASSRLS`, not a superuser) with `select, insert, update, delete` on the tables (read and insert only on `audit_log`); default privileges give it later tables automatically. If the hosted `postgres` role can't grant `BYPASSRLS`, the fallback is one `to fasthyr_api using (true)` policy per table.
- Local: `supabase/seed.sql` turns on login for `fasthyr_api` with a local-only password, and `apps/api/.env.example` `DATABASE_URL` switches to that role. Hosted (dev/QA/prod): one SQL line in the dashboard sets its password; added to `DEPLOYMENT.md` and the FND-007 checklist.

**SQLAlchemy models** (`apps/api/app/models/`): SQLAlchemy 2 typed models (`Mapped[...]`), one file per area (`identity.py`, `audit.py`) on a shared `Base`, mirroring columns, nullability, FKs (including composite), unique constraints and indexes. `app/core/ids.py` adds `new_id()` (UUID v7; Python 3.12 has no built-in). New dependencies: `sqlalchemy[asyncio]`, `asyncpg`, and `alembic` used only for its model-vs-database comparison. The async session itself is FND-004.

**Drift check:** `apps/api/scripts/check_schema_drift.py` connects to `DATABASE_URL`, compares the live `public` schema (after migrations) against the models, prints any difference and exits 1. `make db-drift` runs it; FND-006 CI runs it after applying migrations to a fresh database.

**Tests** (after the hand checks pass), in `apps/api/tests/integration/`, run against local Supabase:
- Anon key: `GET /rest/v1/<table>` for every table in `public` returns no rows (permission denied).
- Every `public` table has RLS on, no policies, and no privileges for `anon` or `authenticated` — this also catches a future table added without the lockdown.
- Signing up a user creates a `profiles` row; a member row pointing at another workspace's department is rejected (composite FK); `update` on `audit_log` is rejected.
- These skip with a clear message when local Supabase isn't running, unless `FASTHYR_REQUIRE_DB=1` (set by CI in FND-006), which turns the skip into a failure.

**Hand checks:** `make db-reset` applies cleanly from scratch; Studio shows the tables; `make db-drift` passes, and fails after deliberately changing a model; anon REST calls are denied; `make lint test` passes.

**Docs:** `DATABASE.md` (conventions for composite FKs, append-only, API role), `MULTI_TENANCY.md` §3 (role name), `DEPLOYMENT.md` (hosted role password step, `DATABASE_URL` user), README (new `make db-drift`), `apps/api/AGENTS.md` models note, AGENTS.md status. Also mark FND-002 Done in BOARD.md and its task file, noting the Google/Microsoft sign-in check still waits on the OAuth apps.

## Log
_(Branch name, decisions, deviations, PR links, review files.)_

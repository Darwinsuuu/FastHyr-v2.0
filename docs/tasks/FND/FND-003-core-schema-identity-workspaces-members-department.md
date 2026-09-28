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
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_

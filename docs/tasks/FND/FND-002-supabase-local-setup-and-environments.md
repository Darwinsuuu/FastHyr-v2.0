# FND-002: Supabase local setup and environments

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | Backlog |
| Size | S |
| Depends on | [FND-001](../FND/FND-001-monorepo-scaffold.md) |
| Requirements | — |
| Gap areas | — |
| Design | — |
| Docs to read | [`architecture/DEPLOYMENT.md`](../../architecture/DEPLOYMENT.md), [`decisions/ADR-002-supabase-auth-db-storage.md`](../../decisions/ADR-002-supabase-auth-db-storage.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Developers run Supabase locally and the development, QA and production projects exist with auth providers configured.

## Scope
**In:**
- `supabase/config.toml` via Supabase CLI; `make setup` runs `supabase start`
- Auth providers in config: Google, Azure, email+password (TA), redirect URLs for local/dev/QA/prod
- Create `fasthyr-dev`, `fasthyr-qa` and `fasthyr-prod` Supabase projects (owner action) and document their env vars
- Custom SMTP placeholder (Resend) in config

**Out:**
- Schema (FND-003)

## Acceptance criteria
- [ ] Local Supabase starts from `make setup`
- [ ] Google and Microsoft sign-in work locally with test OAuth apps
- [ ] Env var names documented in `.env.example` files
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- OAuth app creation in Google Cloud and Azure is a manual owner step — write the checklist in the task log

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Manual: sign in locally with each provider

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_

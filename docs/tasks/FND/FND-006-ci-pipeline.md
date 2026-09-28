# FND-006: CI pipeline

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | Backlog |
| Size | S |
| Depends on | [FND-005](../FND/FND-005-web-skeleton-hosts-tokens-fonts-auth-session-api-c.md) |
| Requirements | — |
| Gap areas | — |
| Design | — |
| Docs to read | [`architecture/DEPLOYMENT.md §3`](../../architecture/DEPLOYMENT.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Every PR is checked automatically for lint, types, tests, migrations, API-contract drift and secrets.

## Scope
**In:**
- GitHub Actions: web job, api job (with Supabase Postgres service), db migration job, contract drift job, gitleaks, audits

**Out:**
- Deploy (FND-007)
- Playwright suite (REL-001)

## Acceptance criteria
- [ ] CI runs on PRs to master and blocks merge on failure
- [ ] Contract job fails if `packages/api-client` is stale
- [ ] Runtime < 10 min
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Open a PR with a deliberate lint error to verify failure

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_

# FND-009: Observability: Sentry, structured logs

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | Ready |
| Size | S |
| Depends on | [FND-005](../FND/FND-005-web-skeleton-hosts-tokens-fonts-auth-session-api-c.md), [FND-008](../FND/FND-008-background-worker-and-job-framework.md) |
| Requirements | NFR-08, NFR-03 |
| Gap areas | — |
| Design | — |
| Docs to read | [`architecture/DEPLOYMENT.md §5`](../../architecture/DEPLOYMENT.md), [`architecture/SECURITY.md §3`](../../architecture/SECURITY.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Errors from web, API and worker reach Sentry with request IDs and without personal data.

## Scope
**In:**
- Sentry SDKs (web, api, worker) with release = git SHA
- PII scrubbing rules; structlog JSON logs with request/job IDs

**Out:**
- —

## Acceptance criteria
- [ ] Test error appears in each Sentry project
- [ ] No emails/names appear in captured events (checked with a fixture)
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_

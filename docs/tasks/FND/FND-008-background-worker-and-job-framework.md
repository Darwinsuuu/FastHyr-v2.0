# FND-008: Background worker and job framework

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | Backlog |
| Size | M |
| Depends on | [FND-004](../FND/FND-004-api-skeleton-auth-request-context-permissions-erro.md) |
| Requirements | NFR-05 |
| Gap areas | — |
| Design | — |
| Docs to read | [`decisions/ADR-009-background-jobs.md`](../../decisions/ADR-009-background-jobs.md), [`architecture/BACKEND.md §4`](../../architecture/BACKEND.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Slow and scheduled work runs reliably in a worker with retries, cron and visible job state.

## Scope
**In:**
- arq WorkerSettings, Redis connection, `enqueue()` helper used by services
- Retry/backoff policy, idempotency helper keyed by entity
- Cron registration pattern; `requeue_stuck_work` sweeper skeleton
- `report_jobs`-style progress pattern (table + `GET /jobs/{id}`)
- Local Redis via Docker in `make dev`

**Out:**
- Specific jobs (their tasks)

## Acceptance criteria
- [ ] A sample job enqueued from an endpoint runs in the worker
- [ ] Failed job retries with backoff then records error
- [ ] Cron job fires locally on schedule
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Integration test with a fake Redis or real Redis service in CI

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_

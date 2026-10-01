# FND-008: Background worker and job framework

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | Done |
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
- [x] A sample job enqueued from an endpoint runs in the worker
- [x] Failed job retries with backoff then records error
- [x] Cron job fires locally on schedule
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Register the hourly cron `expire_credit_batches`: it calls `services/credits.expire_batches(session)` and commits (BILL-002 built it; BACKEND.md §4).
- Register the hourly cron `expire_invites`: it calls `services/invites.expire_invites(session)` and commits (WS-004 built it).

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Integration test with a fake Redis or real Redis service in CI

## Implementation plan
**Queue and worker** (`app/jobs/`, `app/worker.py`)
- `arq` on Redis (`REDIS_URL`). `JobQueue.enqueue(function, *args, key=entity_id)` connects lazily (the API still starts without Redis) and uses `function:key` as the arq job ID, so a second enqueue of the same entity while one is queued, deferred or running is a no-op.
- `@job(retry=RetryPolicy(...), on_failure=...)` wraps every job body: a fresh session per try, rollback on error, `Retry(defer=base * 2^(try-1))` capped at `max_delay`, and after the last try `on_failure` runs in its own committed session (report jobs mark themselves failed with a stable code). arq's `max_tries` is registered from the same policy.
- `app/worker.py` `WorkerSettings` registers functions and crons; `keep_result = 0` because job state people see lives in Postgres (ADR-009). `python -m app.worker` or `make worker` (`arq --watch`).
- Crons (`app/jobs/system.py`): `expire_credit_batches` (hourly, :05), `expire_invites` (hourly, :15), `requeue_stuck_work` (every 10 minutes; re-queues report jobs still queued after 10 minutes; the application and interview tasks add their stuck states).

**Progress pattern** (`report_jobs`, DATABASE.md)
- Migration adds `report_jobs` as documented, plus a `sample` kind for the local demo job. RLS on, no policies.
- `services/jobs.py`: `start_report_job()` (insert, commit, then enqueue), `Progress` (claim → step → done, committing each step, stopping when cancelled), `record_failure()`.
- `GET /v1/jobs/{id}` and `DELETE /v1/jobs/{id}` (cancel): any member, but only the member who started the job sees it; everyone else gets 404.
- `POST /v1/dev/sample-job` (only when `APP_ENV=local`, hidden from OpenAPI) queues `sample_report_job`, which walks N steps and can fail its first tries, to try the framework by hand.

**Local dev and CI**: `make redis-start` runs `redis:7-alpine` as Docker container `fasthyr-redis`; `make dev` starts Redis and runs the worker next to the API and web; `make down` stops them. CI's API job gets a Redis service and `FASTHYR_REQUIRE_REDIS=1`.

**Tests**: unit tests for backoff, retry, the failure hook and the cron schedule; integration tests that run the real worker in burst mode on a per-test queue (job runs from the endpoint, retries then recovers, fails every try and records the error, cancel, sweeper re-queue, enqueue idempotency, and only the requester sees a job).

## Log
- 2026-10-01: branch `feature/foundation-tasks-c4qi1p`. Plan auto-approved (Darwin's standing rule: no plan approvals). First of the remaining FND tasks, done before other work so their dependents unblock.
- Decision: the sample job uses `report_jobs` with a `sample` kind, so the progress pattern (`GET /v1/jobs/{id}`) is exercised end to end now rather than first by the PDF report tasks. Its endpoint exists only when `APP_ENV=local`.
- Decision: a failed report job stores a stable code in `error` (`AppError.code`, else `job_failed`), never the exception message, so no personal data reaches the row.
- Hand test (local Supabase + Redis, `make worker`): a 3-step sample job went queued → running (steps 1, 2, 3) → done; `fail_tries=1` retried after 1 s and finished; `fail_tries=5` retried after 1 s and 2 s, then showed `failed` / `job_failed`; cancelling mid-run stopped it at step 1; `requeue_stuck_work` fired on schedule at 00:40 and 00:50 UTC and re-queued a job row left queued for 15 minutes.

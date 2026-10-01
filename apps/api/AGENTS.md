# apps/api — backend rules

Read [`/AGENTS.md`](../../AGENTS.md) first, then [`docs/architecture/BACKEND.md`](../../docs/architecture/BACKEND.md). This file repeats only the rules that matter on every change.

## Layering
1. **Routers** (`app/api/routers/`) parse input, call `require(...)`, call one service method and return a response model. No SQL, no business logic.
2. **Services** (`app/services/`) hold business rules and transactions.
3. **Repositories** (`app/repositories/`) are the only code that builds queries. Every method takes `workspace_id` and filters by it; cross-workspace access returns 404.
4. **Jobs** (`app/jobs/`) are thin and idempotent: load IDs, call a service, commit.
5. **Integrations** (`app/integrations/`) wrap third-party SDKs so tests can use fakes.

## Always
- AI calls only through `app/ai/` (versioned prompt, JSON schema, `ai_calls` row).
- Credits and money only through `services/credits.py` / billing services, inside transactions.
- Errors are `application/problem+json` with a stable `code`.
- No personal data in URLs, logs or error reports. IDs only.
- Pydantic models for every request and response; mypy strict on `app/`.
- Schema changes: write the SQL migration in `supabase/migrations/` (the source of truth), mirror it in `app/models/`, then `make db-reset db-drift`. New IDs come from `app.core.ids.new_id()` (UUID v7).

## Building an endpoint (FND-004)
- Routes live under `/v1` (`app/main.py` mounts routers on the `v1` router). `/health` stays at the root.
- TA endpoints take `ctx: Annotated[RequestContext, require(Action.X)]` from `app/api/deps.py`: it checks the sign-in token, the `X-Workspace-Id` membership (`403 not_a_member`) and the role against `app/core/permissions.py` (`403 forbidden`). New actions go in `Action` and `MATRIX`, plus the hand-written table in `tests/unit/test_permissions.py`.
- Workspace data goes through a subclass of `app/repositories/base.WorkspaceRepository`, built with `ctx.workspace_id`; use `_scoped()` for every query and `_get_or_404()` for single rows. Department limits come from `ctx.department_ids` / `ctx.sees_all_departments`.
- Raise an `AppError` subclass from `app/core/errors.py` (or add one with a new stable `code`); never `HTTPException`. Add `responses=PROBLEM_RESPONSES` to new routers.
- Tenancy tests: use the `tenancy` fixture (`tests/tenancy/harness.py`): two workspaces, every role, real sign-ins. `tenancy.client("a", Role.RECRUITER)` calls as that member; `tenancy.assert_hidden_from_other_workspace(method, url)` checks every role of the other workspace gets 404.

## Adding a job (FND-008)
- Write the body in `app/jobs/` as `@job(retry=RetryPolicy(...))` `async def name(run: JobRun, workspace_id, entity_id)`: load by ID through a workspace-scoped repository, call a service, commit. It must be safe to run twice (check the row's state first).
- Register it in `app/worker.py` (`register(...)` in `FUNCTIONS`, or `cron(...)` in `CRON_JOBS` with `NO_RETRY`).
- Enqueue from a service **after** `commit()`: `await queue.enqueue("name", workspace_id, entity_id, key=entity_id)`. Routers get the queue from `JobQueueDep`.
- Progress a user waits on goes in `report_jobs` via `services/jobs.py` (`start_report_job`, `Progress`); add the kind to `JOB_FUNCTIONS`.
- Integration tests run the real worker in burst mode on their own queue (see `tests/integration/test_jobs.py`); they need `make redis-start`.

## Sample data (FND-014)
- `scripts/seed.py` builds the Acme Talent workspace from the design. When you add a table the screens show, extend it with the design's sample rows (synthetic people, `.test` emails) and move credits only through `app/services/credits.py`. `tests/unit/test_seed_data.py` checks the sample data stays consistent.

## Commands (from the repo root)
`make api` · `make worker` · `make db-seed` · `make lint-api` · `make test-api` (integration tests need local Supabase and Redis) · `make db-drift` · `make api-client` (after changing the OpenAPI)

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

## Logs and Sentry (FND-009)
- Log with `logging.getLogger("app.<area>")` (or `get_logger()` from `app.core.logging` for key=value fields). Lines are structlog JSON on hosted environments and carry `request_id` / `job_id` automatically; add IDs with `bind_ids(...)`. Log IDs and error class names, never values people typed.
- Unhandled API errors (the 500 handler) and a job's last failed try go to Sentry; handled `AppError`s and log lines don't. Sentry is off while `SENTRY_DSN` is empty. Scrub rules: `app/core/scrub.py`. Test event: `make sentry-test`; local `POST /v1/dev/error` raises through the real handler.

## Adding a job (FND-008)
- Write the body in `app/jobs/` as `@job(retry=RetryPolicy(...))` `async def name(run: JobRun, workspace_id, entity_id)`: load by ID through a workspace-scoped repository, call a service, commit. It must be safe to run twice (check the row's state first).
- Register it in `app/worker.py` (`register(...)` in `FUNCTIONS`, or `cron(...)` in `CRON_JOBS` with `NO_RETRY`).
- Enqueue from a service **after** `commit()`: `await queue.enqueue("name", workspace_id, entity_id, key=entity_id)`. Routers get the queue from `JobQueueDep`.
- Progress a user waits on goes in `report_jobs` via `services/jobs.py` (`start_report_job`, `Progress`); add the kind to `JOB_FUNCTIONS`.
- Integration tests run the real worker in burst mode on their own queue (see `tests/integration/test_jobs.py`); they need `make redis-start`.

## Sending an email (FND-010)
- Render with `app/emails` (`render.render()` for template bodies, `system.py` for fixed system emails); never build HTML from user input by hand.
- In the service's transaction: `message = emails.queue_email(session, ...)`; after `commit()`: `await emails.enqueue(queue, message)`. Never call a provider from a router or service.
- Locally the worker delivers to Mailpit (http://127.0.0.1:54324); tests pass a fake `email_sender` to the worker (`tests/integration/test_emails.py`).

## Calling a model (FND-013)
- Add `app/ai/prompts/<name>@v1.md`, a schema in `app/ai/schemas/`, and a fake answer in `app/ai/fixtures/<name>@v1.json`; call `ai.structured(...)` from a service or job (never a router). Changing a prompt means a new `@vN` file and an `ai_eval` run.
- Tests use `FakeAIClient` (or `AI_FAKE=1`); never call OpenAI from unit or integration tests.

## Sample data (FND-014)
- `scripts/seed.py` builds the Acme Talent workspace from the design. When you add a table the screens show, extend it with the design's sample rows (synthetic people, `.test` emails) and move credits only through `app/services/credits.py`. `tests/unit/test_seed_data.py` checks the sample data stays consistent.

## Candidate notices (COMP-002)
- Consent texts live in `app/compliance/notices/<kind>@v<N>.toml` and are checked against `versions.lock` at start-up and in `tests/unit/test_notices.py`. Never edit a released file: copy it to the next version, edit the copy, then `uv run python -m app.compliance.notices lock`.
- A route that records consent takes the notice id from the request and calls `services/consents.accept(kind, notice_id, now=...)`; store `consent.notice_id` and `consent.at` on the row.

## Files (FND-011)
- Storage goes through `app/integrations/storage.py` (`Bucket`, path builders, `SupabaseStorage`); never call Supabase Storage elsewhere. Signed URLs are capped at 15 minutes.
- Uploads the API must check: `services/files.create_upload()` → the browser uploads → `services/files.promote_pdf()` in the job. Build paths from IDs on your own workspace-scoped rows, never from request input.
- PDF tests use the fixtures in `tests/pdf_fixtures.py`; Storage integration tests use the `storage` fixture (local Supabase with `storage-api`).

## Commands (from the repo root)
`make api` · `make worker` · `make db-seed` · `make lint-api` · `make test-api` (integration tests need local Supabase and Redis) · `make db-drift` · `make api-client` (after changing the OpenAPI)

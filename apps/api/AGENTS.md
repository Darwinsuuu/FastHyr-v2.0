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

## Commands (from the repo root)
`make api` · `make lint-api` · `make test-api` · `make api-client` (after changing the OpenAPI)

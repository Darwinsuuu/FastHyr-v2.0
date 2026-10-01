# FND-009: Observability: Sentry, structured logs

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | In review |
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
- [x] No emails/names appear in captured events (checked with a fixture)
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Auto-approved per the owner's standing rule, 2026-09-29.)_

**API and worker (`apps/api`)**
1. Dependencies: `sentry-sdk[fastapi]`, `structlog`.
2. Settings: `SENTRY_DSN` (empty = Sentry off, nothing sent), `SENTRY_ENVIRONMENT` (default `APP_ENV`), `SENTRY_TRACES_SAMPLE_RATE` (default 0), `GIT_SHA` for the release (falls back to Render's `RENDER_GIT_COMMIT`), `LOG_LEVEL`, `LOG_FORMAT` (`json` | `console`; default `console` locally, `json` elsewhere).
3. `app/core/logging.py`: structlog configured once for the API and the worker. Standard `logging` records (ours, uvicorn, arq) go through the same processors, so every line is one JSON object with `request_id`, `job_id`, `job`, `user_id` and `workspace_id` when known. A scrub processor drops values under personal keys (`email`, `name`, `password`, `token`, …) and masks email addresses inside messages.
4. `app/core/observability.py`: `init_sentry(settings, component)` for `api` and `worker`, with `release` = git SHA, `send_default_pii=False`, no request bodies, cookies or headers, `before_send` / `before_breadcrumb` scrubbers (shared rules in `app/core/scrub.py`), log records as breadcrumbs only (no event per log line), and arq's own integration switched off (it can attach job arguments). `bind_ids()` puts IDs on both the log context and the Sentry scope.
5. Wiring: `RequestIdMiddleware` tags `request_id`; `get_current_user` binds `user_id` (Sentry user = ID only); `get_request_context` binds `workspace_id`; the 500 handler captures the exception; the job wrapper binds `job`, `job_id`, `job_try`, and captures the error after the last try.
6. Test error: `make sentry-test` (or `python -m app.core.observability --component api|worker` in a Render shell) sends one test event; local `POST /v1/dev/error` raises an unhandled error through the real handler.

**Web (`apps/web`)**
7. `@sentry/nextjs`: `instrumentation.ts` + `instrumentation-client.ts`, `app/global-error.tsx`, `withSentryConfig` in `next.config.ts` (source maps upload only when `SENTRY_AUTH_TOKEN` is set). DSN from `NEXT_PUBLIC_SENTRY_DSN` (empty = off), release = `NEXT_PUBLIC_GIT_SHA` or Vercel's commit SHA, environment = `NEXT_PUBLIC_APP_ENV`.
8. `lib/observability/scrub.ts`: same rules as the API, plus URLs lose query strings and fragments, and invite tokens in `/join/…` paths are replaced. API errors add the API's `request_id` as a tag so web and API events join up.
9. `/dev/sentry` (local and development only, like `/dev/ui`): buttons that throw a client error and a server error.

**Tests (after testing by hand)**: API scrub fixture (an event full of emails, names and tokens comes out clean), Sentry off when DSN is empty, request ID tag on a captured 500, job failure captured with job tags, JSON log line carries `request_id`; web scrub fixture in Vitest.

**Docs**: TECH_STACK env lists, both `.env.example` files, DEPLOYMENT.md §5 (how to verify), apps/api and apps/web AGENTS.md, AGENTS.md status.

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
- 2026-10-01: branch `feature/sentry-logging-vkinbd`. Plan auto-approved per the owner's rule. Built so everything is a no-op until the Sentry DSNs are set.
- Checked by hand against a local fake Sentry endpoint: `python -m app.core.observability` sends a worker test event with release and `component` tags; a production web build sent the browser and server test errors from the Sentry check page with release = git SHA, URLs without query strings and no email from the page URL. Real Sentry projects wait on the owner's DSNs (acceptance criterion 1).
- Deviation: the web DSN is `NEXT_PUBLIC_SENTRY_DSN` (the browser needs it at build time), not `SENTRY_DSN` as TECH_STACK.md listed; docs updated. Sentry's arq integration is off: the job wrapper captures the last failed try itself, tagged with IDs, so job arguments never reach Sentry.

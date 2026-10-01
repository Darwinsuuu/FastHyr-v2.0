# FND-007: Deployments: Vercel, Render blueprint, dev and QA environments

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | In review |
| Size | M |
| Depends on | [FND-006](../FND/FND-006-ci-pipeline.md), [FND-008](../FND/FND-008-background-worker-and-job-framework.md) |
| Requirements | NFR-05 |
| Gap areas | — |
| Design | — |
| Docs to read | [`architecture/DEPLOYMENT.md`](../../architecture/DEPLOYMENT.md), [`decisions/ADR-003-hosting-vercel-render.md`](../../decisions/ADR-003-hosting-vercel-render.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
The development (`develop`) and QA (`release`) environments run end to end in the cloud: web on Vercel, API + worker + Redis on Render, their own Supabase projects — deployed from Git.

## Scope
**In:**
- `render.yaml` with api, worker, key value; health checks
- Vercel project with both hosts and env vars
- Protect `master`, `release`, `develop` (PR-only, CI required)
- Migration workflow (auto dev and QA, manual approval prod)
- Domains/DNS for dev and QA (owner action)

**Out:**
- Production cut-over (REL-003)

## Acceptance criteria
- [ ] Merge to `develop` deploys the development environment; merge to `release` deploys QA
- [ ] App host on each environment signs in and calls the API
- [ ] Migrations applied by workflow per environment
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Keep production services defined but scaled to zero/paused until launch if cost matters

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Manual smoke test on the development and QA environments

## Implementation plan
_(Auto-approved per the owner's standing rule, 2026-09-29.)_

Repo-side config only; the owner creates the accounts and enters secrets (DEPLOYMENT.md §7). Nothing in an external account is created or changed by this task's code.

1. **`render.yaml`** (Blueprint): for development (`develop`) and QA (`release`), an API web service (`uvicorn`, health check `/health`), a worker (`python -m app.worker`) and a Key Value instance (`noeviction`, private), region Singapore to sit next to Supabase. Build `uv sync --locked --no-dev` in `apps/api`, Python pinned with `PYTHON_VERSION`. `autoDeployTrigger: checksPass` so a deploy waits for CI and migrations; `buildFilter` on `apps/api/**`. Non-secret values (APP_ENV, WEB_ORIGINS, SITE_URL) in the file; secrets `sync: false`; the worker reads shared secrets from its API service. Production services wait for REL-003 (defined there, so no idle paid services now).
2. **`.github/workflows/migrate.yml`**: `supabase db push --db-url` with the pinned CLI on pushes to `develop` / `release` that touch `supabase/migrations/`; production only by manual dispatch from `master` (the approval step). Repository secrets `SUPABASE_DB_URL_{DEVELOPMENT,QA,PRODUCTION}` rather than GitHub environments, which a private repo only gets on paid plans. Missing secret fails loudly.
3. **`.github/rulesets/protected-branches.json`**: importable ruleset for the three long-lived branches (PR only, five CI checks, no force push or deletion, merge and squash allowed).
4. **Vercel**: configured in the dashboard (root `apps/web`, production branch `master`, branch-scoped Preview env vars and branch domains for `develop` and `release`); no `vercel.json` needed.
5. **Docs**: DEPLOYMENT.md §3, §4 and a new §7 owner checklist (DNS, Supabase, GitHub, Render, Vercel, Resend, smoke test); AGENTS.md status; BOARD.md.

Test plan: no unit tests (config only). By hand: simulate the Render build and start commands from a clean copy of `apps/api` against local Supabase and Redis (health, CORS for the dev origins, signed-in `GET /v1/me`, worker connected to Redis); `supabase db push --db-url` against a database reset to an older migration (applies the rest, no seed, second run is a no-op); actionlint on the workflow.

## Log
- 2026-10-01: branch `feature/deployments-sje0tg`. Plan auto-approved per the owner's rule.
- Checked by hand: the Render build (`uv sync --locked --no-dev` in a clean copy of `apps/api`) and both start commands with development env vars against local Supabase and Redis. `/health` returned ok, a preflight from `https://app.dev.fasthyr.com` was allowed, `GET /v1/me` with a real Supabase session returned the user, and the worker registered with Redis. `supabase db push --yes --db-url` on a database reset to `20260929170000` applied the six newer migrations without seeding; a second push reported up to date. actionlint passed on `migrate.yml`. The Blueprint fields were checked against Render's Blueprint reference (no schema validator reachable from this environment).
- Open, waiting on the owner's accounts: acceptance criteria 1 to 3 need the setup in DEPLOYMENT.md §7, then the smoke test there.
- Deviations: production services are not in `render.yaml` yet (REL-003); previews have one `*.vercel.app` host, so they show the public site only and sign-in is checked on the development hosts; migration secrets are repository secrets, not GitHub environments; the Supabase Auth config is applied in the dashboard, not by `supabase config push` (FND-002 had left that open), because `config.toml` carries local-only values. Resend verifies `fasthyr.com`, not `mail.fasthyr.com` as ADR-008 says, because Resend only sends from the verified domain and the From address is `no-reply@fasthyr.com`.

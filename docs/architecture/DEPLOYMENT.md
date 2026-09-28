# Environments, CI/CD and deployment

## 1. Environments
Each long-lived branch deploys to its own environment ([`process/GIT_CONVENTIONS.md`](../process/GIT_CONVENTIONS.md)).

| Env | Branch | Web | API / worker / Redis | Supabase | Stripe | OpenAI | Resend |
|---|---|---|---|---|---|---|---|
| **local** | any | `pnpm dev` (localhost:3000, app.localhost:3000) | `make api` / `make worker`, Redis via Docker | Supabase CLI (`supabase start`) | test mode + Stripe CLI forwarding | real key with low limits, or fakes (`AI_FAKE=1`) | test key / console |
| **development** | `develop` | `dev.fasthyr.com`, `app.dev.fasthyr.com` | Render services `-dev` | project `fasthyr-dev` | test mode | real key, low spend limit | restricted to allow-listed recipients |
| **release (QA)** | `release` | `qa.fasthyr.com`, `app.qa.fasthyr.com` | Render services `-qa` | project `fasthyr-qa` | test mode | real key, spend limit | restricted to allow-listed recipients |
| **production** | `master` | `fasthyr.com`, `app.fasthyr.com` | Render production services | project `fasthyr-prod` (Pro, PITR) | live mode | production key | production domain |

Feature-branch PRs also get Vercel preview deployments that point at the development API.

### Supabase projects and their env vars
One Supabase project per environment: `fasthyr-dev`, `fasthyr-qa`, `fasthyr-prod`, all in the same region. Locally, `make db-status` prints the same values.

| Env var | Used by | Where to find it (Supabase dashboard) |
|---|---|---|
| `SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_URL` | API / web | Project Settings → Data API → Project URL (`https://<project-ref>.supabase.co`) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | web | Project Settings → API Keys → publishable (or legacy `anon`) key |
| `SUPABASE_SERVICE_ROLE_KEY` | API, worker | Project Settings → API Keys → secret (or legacy `service_role`) key; server only, never in the web app |
| `DATABASE_URL` | API, worker, migrations | Connect → connection string (session pooler for Render) |
| `SUPABASE_JWKS_URL` | API | `https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json` (FND-004) |

Auth settings (providers, redirect URLs, password rules, SMTP) follow `supabase/config.toml`. The OAuth client IDs and secrets go into each project's Authentication → Providers page, never into the repository. The one-time setup checklist is in the FND-002 task log.

## 2. Local development
```
make setup        # pnpm install, uv sync, supabase start (applies migrations + seed)
make dev          # opens Docker if needed, supabase start, then web + api (+ worker, redis later)
make stop         # supabase stop
make api-client   # regenerate packages/api-client from the running API's OpenAPI
make test         # web + api tests
make lint         # eslint, prettier --check, ruff, mypy
make db-reset     # supabase db reset (migrations + seed)
```
`supabase/seed.sql` loads the "Acme Talent" sample workspace from the design.

## 3. Branching and CI (GitHub Actions)
- Branch flow: `feature/*` → `develop` → `release` → `master` (see `process/GIT_CONVENTIONS.md`).
- On every PR (into `develop`, `release` or `master`):
  - **web:** install, typecheck, lint, unit tests, build.
  - **api:** ruff, mypy, pytest (unit + integration + tenancy) against a Supabase CLI Postgres service.
  - **db:** apply all migrations to a fresh database; fail on drift between migrations and SQLAlchemy models (autogenerate diff check).
  - **contract:** regenerate the API client and fail if it differs from the committed one.
  - **security:** gitleaks, pip-audit, pnpm audit (warn-only for low severity).
- Playwright e2e runs on PRs into `release` and nightly against the release (QA) environment.

## 4. Deploy
- **Web:** Vercel Git integration — preview per PR; `develop`, `release` and `master` each deploy to their environment's domains.
- **API + worker:** Render Blueprint (`render.yaml`) defines dev, QA and production services, auto-deploying `develop`, `release` and `master` respectively. Health check `GET /health` (DB + Redis). Worker restarts are safe (jobs idempotent).
- **Database migrations:** a GitHub Action runs `supabase db push` against development on merge to `develop` and against QA on merge to `release`; production is a manual approval step on merge to `master`, run **before** the API deploy that depends on it. Migrations must be backward compatible with the currently running API (expand → migrate → contract).
- **Stripe:** products/prices created by a script (`apps/api/scripts/stripe_bootstrap.py`) per environment; price IDs stored in env config.
- **Supabase Auth config** (providers, redirect URLs, SMTP, email templates) kept in `supabase/config.toml` and applied per environment.

## 5. Observability
- Sentry projects: `web`, `api`, `worker` with release tags = git SHA.
- Logs: Render log streams (JSON). Key metrics logged per job: duration, retries, AI cost.
- Uptime checks on `/health`, apply page and login.

## 6. Launch checklist (summary; full list in task REL-003)
Production Supabase with PITR, custom SMTP, OAuth apps verified (Google, Microsoft) with production redirect URLs; Stripe live mode + webhook; Resend domain verified; OpenAI spend limits; Sentry alerts; backups tested by a restore; legal pages published; rate limits and bot protection on.

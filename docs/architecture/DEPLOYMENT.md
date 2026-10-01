# Environments, CI/CD and deployment

## 1. Environments
Each long-lived branch deploys to its own environment ([`process/GIT_CONVENTIONS.md`](../process/GIT_CONVENTIONS.md)).

| Env | Branch | Web | API / worker / Redis | Supabase | Stripe | OpenAI | Resend |
|---|---|---|---|---|---|---|---|
| **local** | any | `pnpm dev` (fasthyr.localhost:3000, app.fasthyr.localhost:3000) | `make api` / `make worker`, Redis via Docker | Supabase CLI (`supabase start`) | test mode + Stripe CLI forwarding | real key with low limits, or fakes (`AI_FAKE=1`) | test key / console |
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
| `SUPABASE_SERVICE_ROLE_KEY` | API, worker | Project Settings → API Keys → secret (or legacy `service_role`) key; server only, never in the web app. Signs Storage URLs and moves files (FND-011) |
| `DATABASE_URL` | API, worker | Connect → Session pooler connection string, with user `fasthyr_api.<project-ref>` and that role's password (below) |
| `NEXT_PUBLIC_SITE_URL` / `NEXT_PUBLIC_APP_URL` | web | The environment's two hosts, e.g. `https://dev.fasthyr.com` and `https://app.dev.fasthyr.com` (FND-005) |
| `NEXT_PUBLIC_COOKIE_DOMAIN` | web | The hosts' shared parent so one sign-in covers both: `dev.fasthyr.com`, `qa.fasthyr.com`, `fasthyr.com`; locally `fasthyr.localhost` |
| `SUPABASE_JWKS_URL` | API | `https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json` (FND-004) |

**API database role.** The API and worker connect as `fasthyr_api` (created by the first migration: not a superuser, bypasses RLS, table privileges only; ADR-006). Migrations still run as `postgres`. After the first migration reaches a hosted project, turn on its login once in the SQL editor with a new random password kept in your password manager, then use it in `DATABASE_URL`:
```sql
alter role fasthyr_api with login password '<random password>';
```
Locally, `supabase/seed.sql` does this with the password `fasthyr_api_local`.

**Email (FND-010).** The API and worker send through Resend when `RESEND_API_KEY` is set (Resend → API Keys, sending access for the `mail.fasthyr.com` domain). `SITE_URL` is the environment's site host (the invite link is `{SITE_URL}/join/{token}`). In Resend → Webhooks, add `https://<api host>/v1/webhooks/resend` for the delivered, bounced, complained and failed events and copy its signing secret into `RESEND_WEBHOOK_SECRET`. Without a key the API only logs the email's ID (locally it delivers to Mailpit). `POST /v1/dev/test-email` (development only) sends a test to yourself.

**Storage (FND-011).** The buckets come from the migration `20261001120000_storage_buckets.sql`, so `supabase db push` creates them with their size limits and file types. Two settings live in the dashboard: Storage → Settings → global upload file size limit must be at least 500 MB (final interview recordings; needs the Pro plan, as the Free plan caps it at 50 MB), and no storage policies are added for `anon` or `authenticated` (the API signs every URL with `SUPABASE_SERVICE_ROLE_KEY`).

Auth settings (providers, redirect URLs, password rules, SMTP) follow `supabase/config.toml`. The OAuth client IDs and secrets go into each project's Authentication → Providers page, never into the repository. The one-time setup checklist is in the FND-002 task log.

**Auth emails (AUTH-002).** Supabase Auth sends the verification and password-reset emails itself, not the API. For each hosted project:
1. Authentication → URL Configuration: Site URL is the environment's site host (e.g. `https://dev.fasthyr.com`); the recovery link is built from it.
2. Authentication → Emails → Templates: for **Confirm signup** and **Reset password**, copy the subject from `supabase/config.toml` (`[auth.email.template.*]`) and paste the HTML from `supabase/templates/confirmation.html` and `recovery.html`. The links must stay pointed at `/auth/confirm`; Supabase's default template links don't work with it.
3. Authentication → Emails → SMTP Settings (once Resend's `fasthyr.com` domain is verified): host `smtp.resend.com`, port 465, user `resend`, password a Resend API key, sender `no-reply@fasthyr.com`, name `FastHyr`. Supabase's built-in mailer only reaches team members and allows a few emails an hour.
4. Authentication → Rate Limits and Sign In / Providers → Email: link expiry (`otp_expiry`) 3600 s and minimum interval between emails 60 s, as in `config.toml`.

Locally nothing is needed: `make db-start` loads the templates and Mailpit catches every email. After changing a template or `config.toml`, restart local Supabase (`make db-stop db-start`).

## 2. Local development
```
make setup        # pnpm install, uv sync, supabase start (migrations + seed.sql), db-seed
make dev          # opens Docker if needed, supabase start, redis-start, then web + api + worker
make worker       # just the job worker (restarts on code changes)
make redis-start  # local Redis for the job queue (Docker container fasthyr-redis)
make stop         # supabase stop, redis-stop
make api-client   # regenerate packages/api-client from the running API's OpenAPI
make test         # web + api tests
make lint         # eslint, prettier --check, ruff, mypy
make db-reset     # supabase db reset (migrations + seed.sql), then db-seed
make db-seed      # add the Acme Talent sample workspace (skips if it's there)
make db-drift     # fail if app/models and the migrated database disagree
```
`supabase/seed.sql` only sets the local API role password. `make db-seed` (`apps/api/scripts/seed.py`) adds the "Acme Talent" sample workspace from the design; sign in as `dana@acme-talent.test` (Admin, owner), `maria@acme-talent.test` (Recruiter) or `jomar@acme-talent.test` (Hiring manager) with the password `acme-talent-local`. CI runs no seeder, so tests never depend on it.

## 3. Branching and CI (GitHub Actions)
- Branch flow: `feature/*` → `develop` → `release` → `master` (see `process/GIT_CONVENTIONS.md`).
- On every PR (into `develop`, `release` or `master`) and every push to those branches, `.github/workflows/ci.yml` runs five parallel jobs, each built from `make` targets so a red job reproduces locally:
  - **Web:** `make lint-web` (Prettier, token and contrast checks, ESLint, typecheck), `make test-web`, `next build`.
  - **API and database:** `make lint-api` (ruff, mypy), then the pinned Supabase CLI starts a fresh local stack (every migration and the seed applied), `make test-api` with `FASTHYR_REQUIRE_DB=1` and `FASTHYR_REQUIRE_REDIS=1` against a Redis service container (unit, integration and tenancy; a missing database or Redis fails instead of skipping), and `make db-drift` (SQLAlchemy models vs migrations). The db checks share this job so Supabase starts once.
  - **API client up to date:** `make api-client`, then fails if `packages/api-client` differs from the committed one.
  - **Secrets and audits:** gitleaks over the whole history (allowlist in `.gitleaks.toml`: only the fixed local Supabase keys), `pnpm audit --audit-level=moderate` (low only warns), `pip-audit` on the locked API dependencies.
  - **End-to-end (Playwright):** Supabase, the API and a production build of the web app, then `make e2e`. The suite is small, so it runs on every PR for now; REL-001 decides whether the full suite moves to PRs into `release` plus a nightly run against QA.
- Merges are blocked by making these five checks required in the branch rules for `develop`, `release` and `master` (GitHub settings, done by the owner; FND-007 covers the rest of branch protection).

## 4. Deploy
- **Web:** Vercel Git integration — preview per PR; `develop`, `release` and `master` each deploy to their environment's domains.
- **API + worker:** Render Blueprint (`render.yaml`) defines dev, QA and production services, auto-deploying `develop`, `release` and `master` respectively. Health check `GET /health` (DB + Redis). Worker restarts are safe (jobs idempotent).
- **Database migrations:** a GitHub Action runs `supabase db push` against development on merge to `develop` and against QA on merge to `release`; production is a manual approval step on merge to `master`, run **before** the API deploy that depends on it. Migrations must be backward compatible with the currently running API (expand → migrate → contract).
- **Stripe:** products/prices created by a script (`apps/api/scripts/stripe_bootstrap.py`) per environment; price IDs stored in env config.
- **Supabase Auth config** (providers, redirect URLs, SMTP, email templates) kept in `supabase/config.toml` and applied per environment.

## 5. Observability
- Sentry projects: `web`, `api`, `worker` with release tags = git SHA (FND-009).
  - Web (Vercel): `NEXT_PUBLIC_SENTRY_DSN` = the web project's DSN; for readable stack traces also `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT` (source maps upload at build). The release comes from `VERCEL_GIT_COMMIT_SHA`.
  - API and worker (Render): `SENTRY_DSN` = the api project's DSN on the API service and the worker project's DSN on the worker service. The release comes from `RENDER_GIT_COMMIT` (or `GIT_SHA`).
  - An empty DSN sends nothing. Events never carry personal data: scrub rules in `apps/api/app/core/scrub.py` and `apps/web/lib/observability/scrub.ts` (no bodies, cookies, query strings or local variables; user = ID only; emails and tokens masked). Tags: `request_id`, `user_id`, `workspace_id`, `job`, `job_id`, `component`.
  - Check a deployment: API and worker, run `python -m app.core.observability --component api` (or `worker`) in the service's Render shell; web, open `/dev/sentry` on the app host (development only) or watch for real errors.
- Logs: Render log streams, one JSON object per line (`LOG_FORMAT=json` is the default outside local) with `request_id` or `job` / `job_id`, plus `user_id` and `workspace_id` when known. The API writes one `request` line per request (method, route template such as `/v1/invites/{key}`, status, duration) in place of uvicorn's access log, so client IPs and query strings stay out. Key metrics logged per job: duration, retries, AI cost.
- Uptime checks on `/health`, apply page and login.

## 6. Launch checklist (summary; full list in task REL-003)
Production Supabase with PITR, custom SMTP, OAuth apps verified (Google, Microsoft) with production redirect URLs; Stripe live mode + webhook; Resend domain verified; OpenAI spend limits; Sentry alerts; backups tested by a restore; legal pages published; rate limits and bot protection on.

# FND-002: Supabase local setup and environments

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | In review |
| Size | S |
| Depends on | [FND-001](../FND/FND-001-monorepo-scaffold.md) |
| Requirements | — |
| Gap areas | — |
| Design | — |
| Docs to read | [`architecture/DEPLOYMENT.md`](../../architecture/DEPLOYMENT.md), [`decisions/ADR-002-supabase-auth-db-storage.md`](../../decisions/ADR-002-supabase-auth-db-storage.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Developers run Supabase locally and the development, QA and production projects exist with auth providers configured.

## Scope
**In:**
- `supabase/config.toml` via Supabase CLI; `make setup` runs `supabase start`
- Auth providers in config: Google, Azure, email+password (TA), redirect URLs for local/dev/QA/prod
- Create `fasthyr-dev`, `fasthyr-qa` and `fasthyr-prod` Supabase projects (owner action) and document their env vars
- Custom SMTP placeholder (Resend) in config

**Out:**
- Schema (FND-003)

## Acceptance criteria
- [ ] Local Supabase starts from `make setup`
- [ ] Google and Microsoft sign-in work locally with test OAuth apps
- [ ] Env var names documented in `.env.example` files
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- OAuth app creation in Google Cloud and Azure is a manual owner step — write the checklist in the task log

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Manual: sign in locally with each provider

## Implementation plan
Branch: `feature/local-supabase-xcwy54` from `develop`.

**Supabase CLI**
- Add the `supabase` CLI as a pinned root dev dependency (npm package, 2.x), so it installs with `make setup` and everyone runs the same version (`pnpm supabase …`). The only new tool to install is Docker Desktop.
- `supabase init` creates `supabase/config.toml` (`project_id = "fasthyr"`), replacing `supabase/.gitkeep`. Default local ports: API 54321, Postgres 54322, Studio 54323, Mailpit (email catcher) 54324.
- Turn off services we don't use (Realtime, Edge Functions, Analytics) so it starts faster; keep Auth, Postgres, Storage, Studio and Mailpit.

**Auth config (`supabase/config.toml`)**
- `site_url = "http://localhost:3000"`; `additional_redirect_urls` lists `/auth/callback` on every host: `localhost:3000`, `app.localhost:3000`, `dev.fasthyr.com`, `app.dev.fasthyr.com`, `qa.…`, `app.qa.…`, `fasthyr.com`, `app.fasthyr.com`.
- JWT expiry 1 h; email + password with verification required, min 8 characters; reset link valid 1 h, resend after 60 s (FR-AUTH-01..03, SECURITY.md §1).
- `[auth.external.google]` and `[auth.external.azure]` enabled, with client IDs and secrets read from `supabase/.env` via `env(...)` (never committed; `supabase/.env.example` lists the names). Azure uses the `common` tenant so work and personal Microsoft accounts both work.
- `[auth.email.smtp]` placeholder for Resend (`smtp.resend.com:465`, user `resend`, password `env(RESEND_API_KEY)`), disabled locally so Mailpit catches every email.

**Makefile**
- `setup`: also runs `supabase start` (Docker must be running).
- New `db-start`, `db-stop`, `db-status` (prints local URLs and keys); `db-reset` runs `supabase db reset`. `make dev` stays as is (Supabase keeps running in Docker between sessions).

**Env vars**
- `apps/api/.env.example`: `DATABASE_URL`, `SUPABASE_URL` filled with local defaults; `SUPABASE_SERVICE_ROLE_KEY` with a note to copy it from `make db-status`.
- `apps/web/.env.example`: `NEXT_PUBLIC_SUPABASE_URL` local default, anon key from `make db-status`.
- No app code reads these yet (FND-003/004/005 do), so no settings code changes.

**Remote projects (owner steps, checklist in the Log)**
- Create `fasthyr-dev`, `fasthyr-qa`, `fasthyr-prod` in one region; turn on Google, Azure and email providers with the redirect URLs above; turn on the leaked-password check where the plan allows it.
- Google Cloud OAuth client and Azure app registration, each with redirect URIs `http://127.0.0.1:54321/auth/v1/callback` plus `https://<project-ref>.supabase.co/auth/v1/callback` for each project. (Separate test and production apps are fine; the checklist says which URIs go where.)
- DEPLOYMENT.md gets a table of which env var comes from which Supabase project setting. Pushing `config.toml` to the remote projects automatically is left to FND-007 (deployments).

**Docs:** README run-locally (Docker Desktop in tools, new "Start Supabase" step, local URLs table with Studio and Mailpit, troubleshooting), DEPLOYMENT.md env table, AGENTS.md status. Also mark FND-001 Done in BOARD.md and its task file.

**Tests:** config only, so no unit tests. Manual: `make setup` from a clean clone starts Supabase; email sign-up lands in Mailpit; Google and Microsoft sign-in tested by opening `http://127.0.0.1:54321/auth/v1/authorize?provider=google` (and `azure`) and checking the user appears in Studio. The web sign-in page itself comes in FND-005. I can verify startup and email here; the two OAuth providers need the owner's test OAuth apps.

## Log
- 2026-09-28: plan written; branch `feature/local-supabase-xcwy54`.
- Supabase CLI 2.118.0 pinned as a root dev dependency. It ships as per-platform npm packages (no install script), so `pnpm-workspace.yaml` needs no change.
- Also turned off Storage vector buckets (unused). The leaked-password check is a hosted-only setting, so it is on the owner checklist rather than in `config.toml`.
- Verified here: `supabase start` from a clean state (images pulled, all services healthy); Google and Azure show as enabled; sign-up rejects a 7-character password; a new email account cannot sign in until confirmed and the confirmation email lands in Mailpit; `supabase/.env` values reach the Azure authorize URL after `make db-stop db-start`; `make db-status` and `make db-reset` work. Google and Microsoft sign-in end to end needs the owner's OAuth apps (checklist below).
- Added an empty `supabase/seed.sql` so `db reset` doesn't warn; FND-014 fills it.
- Deviation: `config.toml` holds the redirect URLs for every environment, but pushing it to the remote projects (`supabase config push`) is left to FND-007; until then the owner applies the auth settings in the dashboard (checklist below).

### Owner checklist: OAuth apps and Supabase projects
Do these once. Secrets go only into `supabase/.env` (local) and the Supabase dashboard (remote), never into the repository.

**1. Google OAuth client** (Google Cloud Console → APIs & Services)
1. Create a project `FastHyr` (or reuse one). OAuth consent screen: External, app name `FastHyr`, support email, scopes `openid`, `email`, `profile`. While in testing mode, add your test Google accounts as test users.
2. Credentials → Create credentials → OAuth client ID → Web application, name `FastHyr local + dev`.
3. Authorised JavaScript origins: `http://localhost:3000`, `http://app.localhost:3000`.
4. Authorised redirect URIs: `http://127.0.0.1:54321/auth/v1/callback`, plus `https://<project-ref>.supabase.co/auth/v1/callback` for `fasthyr-dev` and `fasthyr-qa` once they exist.
5. Copy the client ID and secret into `supabase/.env` (`SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID`, `…_SECRET`).
6. For production, create a second client `FastHyr production` with only the `fasthyr-prod` callback URI and `https://fasthyr.com`, `https://app.fasthyr.com` as origins; the consent screen needs Google verification before launch (REL-003).

**2. Microsoft app registration** (Azure portal → Microsoft Entra ID → App registrations)
1. New registration `FastHyr local + dev`. Supported account types: *Accounts in any organizational directory and personal Microsoft accounts*.
2. Redirect URI (Web): `http://127.0.0.1:54321/auth/v1/callback`; add the `fasthyr-dev` and `fasthyr-qa` callback URIs under Authentication once they exist.
3. Certificates & secrets → New client secret; copy the **Value** (not the ID).
4. API permissions: Microsoft Graph delegated `openid`, `email`, `profile`, `User.Read` (default).
5. Copy the Application (client) ID and the secret value into `supabase/.env` (`SUPABASE_AUTH_EXTERNAL_AZURE_CLIENT_ID`, `…_SECRET`).
6. For production, a second registration `FastHyr production` with only the `fasthyr-prod` callback URI.

**3. Test locally**
1. `make db-stop db-start` so Supabase reads `supabase/.env`.
2. Open `http://127.0.0.1:54321/auth/v1/authorize?provider=google&redirect_to=http://localhost:3000/auth/callback`, sign in, and check the user appears in Studio → Authentication (http://localhost:54323). The browser then shows a "page not found" from the web app, which is expected until FND-005 adds `/auth/callback`.
3. Repeat with `provider=azure&scopes=email` (Microsoft only returns the email address when the `email` scope is asked for; FND-005 passes it from the sign-in page).

**4. Supabase projects** (supabase.com dashboard)
1. Create `fasthyr-dev`, `fasthyr-qa` and `fasthyr-prod` in one organization and one region (production on the Pro plan for PITR, per the deployment doc). Save each database password in your password manager.
2. In each project, Authentication → URL Configuration: Site URL `https://dev.fasthyr.com`, `https://qa.fasthyr.com` or `https://fasthyr.com`; redirect URLs `https://<site host>/auth/callback` and `https://app.<site host>/auth/callback` for that environment (dev also allows `http://localhost:3000/auth/callback` and `http://app.localhost:3000/auth/callback`).
3. Authentication → Providers: Email on with "Confirm email", minimum password length 8, leaked-password protection on where the plan allows it; Google and Azure on with that environment's client ID and secret (Azure URL `https://login.microsoftonline.com/common/v2.0`).
4. Authentication → Rate limits / Email: reset link and OTP expiry 3600 s, 60 s between emails. Custom SMTP (Resend) is turned on in FND-010.
5. Note each project's URL, keys and connection string; the env var names are in `docs/architecture/DEPLOYMENT.md` §1. They are entered into Vercel and Render in FND-007.

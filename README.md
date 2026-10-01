# FastHyr v2.0

**Every applicant, heard.** FastHyr is an AI interviewer for Talent Acquisition teams: share one apply link, and FastHyr screens every résumé, runs an adaptive video or voice interview with each qualified applicant, and delivers explainable assessments your team can act on.

- **Start here:** [`AGENTS.md`](AGENTS.md) (for people and AI agents alike)
- **Docs:** [`docs/README.md`](docs/README.md)
- **Task board:** [`docs/tasks/BOARD.md`](docs/tasks/BOARD.md)

Stack: Next.js · FastAPI · Supabase · OpenAI · Stripe · Resend · Vercel · Render.

## Run locally

### 1. Install the tools (once)
| Tool | Version | Install (macOS) |
|---|---|---|
| Node.js | 24 LTS (pinned in `.nvmrc`) | `brew install nvm`, then `nvm install 24 && nvm use 24` |
| pnpm | 10 (pinned in `package.json`) | `corepack enable` (ships with Node), or `npm install -g pnpm@10` |
| uv | latest | `brew install uv` (it downloads Python 3.12 by itself) |
| make | any | included with Xcode Command Line Tools (`xcode-select --install`) |
| Docker Desktop | latest | download from docker.com, or `brew install --cask docker`; open it once so it keeps running |

The Supabase CLI is not installed separately: `make setup` installs a pinned version with the other packages (run it as `pnpm supabase …`).

Check them with `node -v` (v24.x), `pnpm -v` (10.x), `uv --version` and `docker info` (no error means Docker is running). If `nvm` is not found after installing it, follow the shell setup lines that `brew info nvm` prints.

### 2. Install dependencies and start Supabase
Start Docker Desktop, then from the repository root (run again after pulling changes that add packages):
```bash
make setup   # pnpm install, uv sync in apps/api, then starts local Supabase
```
The first run downloads the Supabase Docker images and takes a few minutes. Supabase keeps running in Docker until you run `make db-stop` or quit Docker; start it again with `make db-start`.

| What | URL |
|---|---|
| Supabase Studio (tables, users, storage) | http://localhost:54323 |
| Mailpit (every email local Auth sends lands here) | http://localhost:54324 |
| Supabase API (Auth, Storage) | http://127.0.0.1:54321 |
| Postgres | `postgresql://postgres:postgres@127.0.0.1:54322/postgres` |

`make db-status` prints these plus the local keys.

### 3. Environment variables
Both apps still run with defaults. To override, copy the examples; `.env` files are never committed.
```bash
cp apps/web/.env.example apps/web/.env.local
cp apps/api/.env.example apps/api/.env
cp supabase/.env.example supabase/.env   # only for Google / Microsoft sign-in
```
Use `fasthyr.localhost` and `app.fasthyr.localhost`, not plain `localhost`: browsers only share one sign-in between the two hosts when they sit under a common domain. Chrome, Edge and Firefox resolve `*.localhost` by themselves; for Safari, add `127.0.0.1 fasthyr.localhost app.fasthyr.localhost` to `/etc/hosts` once. If you copied the env files before FND-005, copy `apps/web/.env.example` again (new `NEXT_PUBLIC_*` URLs and `NEXT_PUBLIC_COOKIE_DOMAIN`), update `WEB_ORIGINS` in `apps/api/.env`, and restart Supabase so it picks up the new redirect URLs.

To sign in locally without OAuth, open http://fasthyr.localhost:3000/login, enter any email and a password of 8 or more characters, and press Continue. That creates the account and sends a verification email, which you open from Mailpit at http://127.0.0.1:54324. "Forgot password?" on the same page sends a reset link to Mailpit the same way. If you pulled AUTH-002 into a Supabase that was already running, restart it once (`make db-stop db-start`) so it picks up the branded email templates; without that, the links in those emails fail. With no workspace yet you land on Choose workspace, where you can create one (you become its admin and land on a placeholder Getting started page). Invites can't be sent from the app until WS-004; to try joining, create an invite in the database (see "Try joining a workspace" under Troubleshooting).

The Supabase keys come from `make db-status` (the local keys are the same on every machine). Google and Microsoft sign-in need your own test OAuth apps; the steps are in the [FND-002 task log](docs/tasks/FND/FND-002-supabase-local-setup-and-environments.md#log). After editing `supabase/.env`, restart Supabase with `make db-stop db-start`.

#### Local Supabase or the hosted `fasthyr-dev` project
Your `.env` files decide which Supabase the apps talk to. Use local (Docker) day to day: it's fast, works offline, and `make db-reset` only touches your own copy. Point at the hosted `fasthyr-dev` project when you want to test against the real network, for example connection speed. Keep both sets in the file and comment out the one you're not using:
```bash
# apps/api/.env
# Local Supabase (values from `make db-status`)
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_SERVICE_ROLE_KEY=<local Secret key>
DATABASE_URL=postgresql://fasthyr_api:fasthyr_api_local@127.0.0.1:54322/postgres

# Hosted fasthyr-dev (values from the Supabase dashboard)
# SUPABASE_URL=https://<project-ref>.supabase.co
# SUPABASE_SERVICE_ROLE_KEY=<fasthyr-dev secret key>
# DATABASE_URL=<fasthyr-dev Session pooler connection string, user fasthyr_api.<project-ref>>
```
The API connects as its own database role, `fasthyr_api`, not as `postgres`. Locally `make db-reset` gives it the password `fasthyr_api_local`; for a hosted project, set its password once as described in [DEPLOYMENT.md](docs/architecture/DEPLOYMENT.md#supabase-projects-and-their-env-vars).
Do the same for `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` in `apps/web/.env.local`, then restart `make dev`. Never put hosted keys in `.env.example` or any committed file.

### 4. Start everything
```bash
make dev     # opens Docker Desktop if needed, starts Supabase, then web and API; Ctrl+C stops the apps
```
Supabase keeps running after Ctrl+C, so the next `make dev` starts in seconds. `make stop` stops Supabase too, and `make down` stops everything: the web app, the API, Supabase, and Docker Desktop. Your local data is kept either way.
| What | URL |
|---|---|
| Public site | http://fasthyr.localhost:3000 |
| Sign in | http://fasthyr.localhost:3000/login |
| Local emails (Mailpit) | http://127.0.0.1:54324 |
| TA app (sign in first) | http://app.fasthyr.localhost:3000 |
| UI kit gallery (sign in first; local and development only) | http://app.fasthyr.localhost:3000/dev/ui |
| API health check | http://localhost:8000/health → `{"status":"ok"}` |
| API docs (Swagger) | http://localhost:8000/v1/docs |
| API schema (OpenAPI) | http://localhost:8000/v1/openapi.json |

Run one app at a time with `make web` or `make api`. Web changes reload in the browser and the API restarts on save.

#### One-word shortcut (optional)
Add an alias to your shell once, then type `fasthyr` in any Terminal window to start everything:
```bash
echo "alias fasthyr='cd ~/Documents/GitHub/FastHyr-v2.0 && make dev'" >> ~/.zshrc
source ~/.zshrc
```
Change the path if your checkout lives somewhere else.

### 5. Test the UI at different screen sizes
In Chrome, open DevTools (Cmd+Option+I / Ctrl+Shift+I), turn on the device toolbar (Cmd+Shift+M / Ctrl+Shift+M) and check 360, 768, 1024 and 1440 px wide, as the [Definition of Done](docs/process/DEFINITION_OF_DONE.md) requires.

### 6. Lint and tests
```bash
make lint    # Prettier, ESLint, tsc, ruff, mypy
make test    # Vitest (web) and pytest (API)
make e2e     # Playwright browser tests; needs `make dev` running in another terminal
```
Before the first `make e2e`, install Playwright's browser once with `pnpm --filter web exec playwright install chromium`.

### Other commands
| Command | What it does |
|---|---|
| `make api-client` | Regenerates the TypeScript client in `packages/api-client` from the API's OpenAPI schema |
| `make worker` | Background worker (added in FND-008) |
| `make stop` | Stops local Supabase (your data is kept) |
| `make down` | Stops the web app, API and Supabase, then quits Docker Desktop (your data is kept) |
| `make db-start` / `make db-stop` | Starts or stops only local Supabase (your data is kept) |
| `make db-status` | Prints local Supabase URLs and keys |
| `make db-reset` | Recreates the local database from `supabase/migrations` and `supabase/seed.sql`, then adds the sample workspace (deletes local data) |
| `make db-seed` | Adds the Acme Talent sample workspace; sign in as `dana@acme-talent.test` with password `acme-talent-local` |
| `make db-drift` | Checks that the API's database models match the migrated local database |

### Troubleshooting
| Problem | Fix |
|---|---|
| `make: pnpm: No such file or directory` | Run `corepack enable` (or `npm install -g pnpm@10`), then `make setup` |
| `Unsupported engine` warning | Switch to Node 24 with `nvm use` |
| `Address already in use` on :3000 or :8000 | Another dev server is running; stop it, or find it with `lsof -i :3000` |
| Web shows old code after pulling | Stop `make dev`, run `make setup`, start again |
| `Docker is not running` or `Cannot connect to the Docker daemon` | Open Docker Desktop and wait until it says Engine running, then run the command again. `make dev` opens it for you when it is installed |
| `docker: command not found` with Docker Desktop open | Open a new Terminal window; if it persists, Docker Desktop → Settings → Advanced → install CLI tools for the System |
| Supabase port already allocated (543xx) | Another Supabase project is running; stop it with `pnpm supabase stop --project-id <its id>`, or `docker ps` to find it |
| OAuth error `redirect_uri_mismatch` | The OAuth app is missing `http://127.0.0.1:54321/auth/v1/callback` as a redirect URI |

#### Try joining a workspace
Sending invites arrives with WS-004. Until then, create one in Supabase Studio's SQL editor (http://127.0.0.1:54323) for a workspace you made, with the email of a second account (lowercase):

```sql
insert into invites (workspace_id, email, role, code, token_hash, invited_by)
select id, 'teammate@example.com', 'recruiter', 'TEST-0001', md5(random()::text), owner_id
from workspaces where name = 'Acme Talent';
```

Sign in as that account and paste `TEST-0001` (or `fasthyr.localhost:3000/join/TEST-0001`) into Join a workspace. Each code works once; use a new code for the next try.

Status: monorepo scaffold (FND-001), local Supabase (FND-002), core schema (FND-003), the API skeleton (FND-004: sign-in checks, workspace context, permissions, error format, `GET /v1/me`) the web skeleton (FND-005: site and app hosts, design tokens and fonts, sign-in session, typed API client), the UI kit (FND-012) employer sign-in (AUTH-001: Google, Microsoft and email + password at `/login`, log out) password reset and email verification (AUTH-002: forgot-password modal, `/reset-password`, `/verify-email`, branded auth emails) and Choose workspace (AUTH-003: create a workspace or join one with an invite code at `/workspaces`) in place; see the task board for what's next.

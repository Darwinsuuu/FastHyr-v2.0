# FND-001: Monorepo scaffold

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | In review |
| Size | M |
| Depends on | — |
| Requirements | — |
| Gap areas | — |
| Design | — |
| Docs to read | [`architecture/ARCHITECTURE.md §4`](../../architecture/ARCHITECTURE.md), [`architecture/TECH_STACK.md`](../../architecture/TECH_STACK.md), [`decisions/ADR-001-monorepo-nextjs-fastapi.md`](../../decisions/ADR-001-monorepo-nextjs-fastapi.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
The repository has the target layout with an empty-but-running Next.js app, FastAPI app and shared tooling, so every later task has a place to land.

## Scope
**In:**
- pnpm workspace with `apps/web` (Next.js App Router, TS strict) and `packages/api-client` (empty package)
- `apps/api` with uv, FastAPI app factory, `GET /health`, ruff + mypy config
- Root `Makefile` targets: setup, dev, api, worker, web, test, lint, api-client, db-reset
- `.editorconfig`, `.gitignore` (incl. `.env*`), Prettier/ESLint config, `.env.example` in each app
- Nested `apps/web/AGENTS.md` and `apps/api/AGENTS.md` pointing to FRONTEND.md / BACKEND.md with the layering rules

**Out:**
- Database, auth, UI (later FND tasks)

## Acceptance criteria
- [x] `make setup && make dev` starts web on :3000 and API on :8000
- [x] `GET /health` returns `{status: ok}`
- [x] `make lint` and `make test` run (with placeholder tests) and pass
- [x] Folder layout matches ARCHITECTURE.md §4
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Use Python 3.12 and the current Node LTS; pin in `.tool-versions` or `.nvmrc` + `pyproject`

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- CI-equivalent commands run locally

## Implementation plan
Branch: `feature/monorepo-scaffold` from `develop`.

**Versions (pinned):** Node 24 LTS (`.nvmrc`, `engines`), pnpm 10 (`packageManager`), Python 3.12 (`apps/api/.python-version`, `requires-python = ">=3.12,<3.13"`). Latest stable Next.js (App Router) + React, TypeScript strict.

**Root files**
- `package.json` (private, workspace scripts), `pnpm-workspace.yaml` (`apps/web`, `packages/*`), `pnpm-lock.yaml`
- `.editorconfig`, `.gitignore` (node, Next, Python, uv, `.env*` except `.env.example`), `.prettierrc` + `.prettierignore`, `.nvmrc`
- `Makefile` with targets:
  - `setup`: `pnpm install` + `uv sync` in `apps/api`
  - `dev`: runs `api` and `web` in parallel (`make -j2`), web on :3000, API on :8000
  - `api`: `uv run uvicorn app.main:app --reload --port 8000`
  - `web`: `pnpm --filter web dev`
  - `worker`: placeholder that prints "added in FND-008" (arq lands there)
  - `lint`: web (ESLint, Prettier check, `tsc --noEmit`) + api (ruff check, ruff format --check, mypy strict on `app/`)
  - `test`: Vitest (web) + pytest (api)
  - `api-client`: dumps the FastAPI OpenAPI schema and runs `openapi-typescript` into `packages/api-client/src/schema.d.ts`
  - `db-reset`: placeholder that prints "added in FND-002" (Supabase CLI lands there)
- Empty `supabase/` and `.github/workflows/` folders (`.gitkeep`) so the layout matches ARCHITECTURE.md §4. CI itself is FND-006.

**`apps/web`**
- Next.js App Router, `app/layout.tsx` + a plain `app/page.tsx` placeholder (no design system, fonts or Tailwind yet, that's FND-005/FND-012)
- ESLint (`eslint-config-next`, flat config), Vitest with one placeholder test
- `.env.example` listing the web env vars from TECH_STACK.md with comments
- `AGENTS.md`: points to FRONTEND.md, repeats the rules that matter most (browser talks to FastAPI only, generated client, copy in `messages/en.json`, mobile first)

**`packages/api-client`**
- Empty TS package (`@fasthyr/api-client`) with `openapi-typescript` + `openapi-fetch`, filled by `make api-client`

**`apps/api`**
- `pyproject.toml` + `uv.lock`: FastAPI, uvicorn, pydantic-settings; dev: pytest, httpx, ruff, mypy
- `app/main.py`: `create_app()` factory, CORS from `WEB_ORIGINS`, `GET /health` → `{"status": "ok"}`
- `app/core/config.py`: pydantic-settings `Settings` (only `APP_ENV` and `WEB_ORIGINS` for now)
- Empty packages from BACKEND.md §1 are **not** created yet; each later task adds its own folder
- `tests/unit/test_health.py`: `/health` returns 200 `{"status": "ok"}`
- `.env.example` listing the API env vars from TECH_STACK.md with comments
- `AGENTS.md`: points to BACKEND.md with the layering rules (routers → services → repositories, workspace scope, AI only via `app/ai/`)

**Docs:** update README quick start (`make setup`, `make dev`), AGENTS.md "Current status", BOARD.md status.

**Tests:** `/health` test (API) and one placeholder Vitest test. No other tests needed.

**Open questions:** none. `make lint test` passing is verified locally and pasted in the PR; CI runs it once FND-006 lands.

## Log
- 2026-09-28: plan written and approved by the owner. Branch `feature/monorepo-scaffold`.
- Deviation: `make lint` also runs `tsc --noEmit` for `packages/api-client`, and the API's test client uses `httpx2` (Starlette deprecates `httpx` for `TestClient`).
- `apps/api` and `packages/api-client` exist, but the BACKEND.md sub-packages (`models/`, `services/`…) and `supabase/` contents are left for the tasks that need them; `supabase/` and `.github/workflows/` hold a `.gitkeep`.

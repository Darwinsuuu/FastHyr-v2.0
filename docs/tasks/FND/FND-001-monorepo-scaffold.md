# FND-001: Monorepo scaffold

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | Ready |
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
- [ ] `make setup && make dev` starts web on :3000 and API on :8000
- [ ] `GET /health` returns `{status: ok}`
- [ ] `make lint` and `make test` run (with placeholder tests) and pass
- [ ] Folder layout matches ARCHITECTURE.md §4
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Use Python 3.12 and the current Node LTS; pin in `.tool-versions` or `.nvmrc` + `pyproject`

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- CI-equivalent commands run locally

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_

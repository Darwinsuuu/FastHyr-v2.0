# FastHyr monorepo commands. Run `make setup` once, then `make dev`.
# Local Supabase runs in Docker, so Docker Desktop must be running for setup and db-* targets.
.PHONY: setup dev stop down api worker web redis-start redis-stop lint lint-web lint-api test test-web test-api e2e api-client db-start db-stop db-status db-reset db-drift

API_DIR := apps/api

# Docker Desktop installs its command here when it isn't added to the system PATH.
export PATH := $(HOME)/.docker/bin:$(PATH)

setup:
	pnpm install
	cd $(API_DIR) && uv sync
	$(MAKE) db-start

# One command for local development: opens Docker if needed, starts Supabase and Redis, then
# runs web on :3000, API on :8000 and the job worker side by side. Ctrl+C stops the apps;
# Supabase and Redis keep running.
dev: db-start redis-start
	$(MAKE) -j3 api web worker

api:
	cd $(API_DIR) && uv run uvicorn app.main:app --reload --port 8000

web:
	pnpm --filter web dev

# The arq job worker (FND-008); restarts when app/ changes.
worker:
	cd $(API_DIR) && uv run arq app.worker.WorkerSettings --watch app

# Local Redis for the job queue, in Docker.
redis-start:
	@scripts/redis-start.sh

redis-stop:
	-docker stop fasthyr-redis

lint: lint-web lint-api

lint-web:
	pnpm format:check
	pnpm --filter web lint
	pnpm --filter web typecheck
	pnpm --filter @fasthyr/api-client typecheck

lint-api:
	cd $(API_DIR) && uv run ruff check .
	cd $(API_DIR) && uv run ruff format --check .
	cd $(API_DIR) && uv run mypy

test: test-web test-api

test-web:
	pnpm --filter web test

test-api:
	cd $(API_DIR) && uv run pytest

# Browser tests of the core journeys (Playwright). Needs `make dev` running in another terminal.
e2e:
	pnpm --filter web e2e

# Regenerate the TypeScript client types from the FastAPI OpenAPI schema.
api-client:
	cd $(API_DIR) && uv run python scripts/export_openapi.py openapi.json
	pnpm --filter @fasthyr/api-client generate

# Local Supabase (Auth, Postgres, Storage, Studio, Mailpit). It keeps running until db-stop.
db-start:
	@scripts/ensure-docker.sh
	pnpm supabase start

db-stop:
	pnpm supabase stop

# Stops local Supabase (the apps stop with Ctrl+C). Docker Desktop itself stays open.
stop: db-stop redis-stop

# Stops everything make dev started: web, API, worker, Supabase, Redis, then quits Docker Desktop
# on macOS.
down:
	@scripts/stop-all.sh

# Local URLs and keys to copy into the .env files.
db-status:
	pnpm supabase status

# Recreates the local database from supabase/migrations and supabase/seed.sql.
db-reset:
	pnpm supabase db reset

# Fails if the SQLAlchemy models (apps/api/app/models) and the migrated database disagree.
db-drift:
	cd $(API_DIR) && uv run python scripts/check_schema_drift.py

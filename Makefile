# FastHyr monorepo commands. Run `make setup` once, then `make dev`.
# Local Supabase runs in Docker, so Docker Desktop must be running for setup and db-* targets.
.PHONY: setup dev api worker web lint lint-web lint-api test test-web test-api api-client db-start db-stop db-status db-reset

API_DIR := apps/api

setup:
	pnpm install
	cd $(API_DIR) && uv sync
	$(MAKE) db-start

# Web on :3000 and API on :8000, side by side. Ctrl+C stops both.
dev:
	$(MAKE) -j2 api web

api:
	cd $(API_DIR) && uv run uvicorn app.main:app --reload --port 8000

web:
	pnpm --filter web dev

worker:
	@echo "The background worker is added in FND-008."

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

# Regenerate the TypeScript client types from the FastAPI OpenAPI schema.
api-client:
	cd $(API_DIR) && uv run python scripts/export_openapi.py openapi.json
	pnpm --filter @fasthyr/api-client generate

# Local Supabase (Auth, Postgres, Storage, Studio, Mailpit). It keeps running until db-stop.
db-start:
	@docker info >/dev/null 2>&1 || { echo "Docker is not running. Install Docker Desktop, open it, wait until it says Engine running, then run make db-start."; exit 1; }
	pnpm supabase start

db-stop:
	pnpm supabase stop

# Local URLs and keys to copy into the .env files.
db-status:
	pnpm supabase status

# Recreates the local database from supabase/migrations and supabase/seed.sql.
db-reset:
	pnpm supabase db reset

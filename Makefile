# FastHyr monorepo commands. Run `make setup` once, then `make dev`.
.PHONY: setup dev api worker web lint lint-web lint-api test test-web test-api api-client db-reset

API_DIR := apps/api

setup:
	pnpm install
	cd $(API_DIR) && uv sync

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

db-reset:
	@echo "Local Supabase is added in FND-002."

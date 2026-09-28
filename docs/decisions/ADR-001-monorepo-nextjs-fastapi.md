# ADR-001: Monorepo with a Next.js web app, a FastAPI API and a Python worker

- **Status:** Accepted
- **Date:** 2026-09-29
- **Deciders:** Darwin Labiste (product owner)

## Context
FastHyr needs a rich TA web app, public candidate pages, and a backend that runs AI screening, interviews, scoring, billing and email. The team is small and uses AI coding agents, which work best when everything lives in one repository with one set of docs.

## Decision
- One Git repository (this one), organised as a monorepo:
  - `apps/web`: Next.js (App Router, TypeScript) for the marketing site, candidate pages and the TA app.
  - `apps/api`: FastAPI (Python 3.12) for the HTTP API **and** the background worker (same codebase, two entry points).
  - `packages/api-client`: TypeScript types and client generated from the FastAPI OpenAPI schema.
  - `supabase/`: database migrations, seed data and local Supabase config.
  - `docs/`: this documentation.
- Tooling: `pnpm` workspaces for JS, `uv` for Python, a root `Makefile` for common commands.

## Consequences
- One PR can change the API contract and the UI together; the generated client keeps them in sync.
- Python owns all business logic; the web app stays a thin client (see ADR-006).
- Two languages to maintain; conventions for each are in `docs/architecture/FRONTEND.md` and `BACKEND.md`.

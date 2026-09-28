# ADR-006: The browser talks to FastAPI only

- **Status:** Accepted
- **Date:** 2026-09-29

## Context
Supabase lets browsers query Postgres directly with Row-Level Security. FastHyr has complex rules (credits, pipeline locking, stage transitions, AI jobs, department scoping) that would be duplicated or hard to express in RLS.

## Decision
- The browser uses Supabase **only** for authentication (sign-in, session refresh, sign-out).
- All data reads and writes go through **FastAPI**, which verifies the Supabase JWT, resolves the active workspace and role, and enforces permissions.
- Files move directly between the browser and Supabase Storage using **signed upload/download URLs** that the API issues after its own checks.
- The API connects to Postgres with a dedicated server role. RLS is **enabled on every table with no policies for `anon` and `authenticated`**, so the public Supabase keys cannot read or write business data even if misused.

## Consequences
- One place for business rules and audit logging.
- Slightly more API code than direct Supabase queries; the generated TypeScript client offsets this.
- Realtime UI updates (e.g. "Processing résumé" → "Invited") use polling via TanStack Query in MVP; Supabase Realtime is not used.

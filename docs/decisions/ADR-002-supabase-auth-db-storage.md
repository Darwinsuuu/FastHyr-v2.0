# ADR-002: Supabase for Auth, Postgres and Storage

- **Status:** Accepted (environment list amended by ADR-019)
- **Date:** 2026-09-29

## Context
We need user authentication (Google, Microsoft, email + password for TA users; Google and Microsoft for candidates), a relational database, and private file storage for résumés, recordings and generated PDFs.

## Decision
- **Supabase Auth** for every human user (TA members and candidates) in one Supabase project per environment. Providers: Google, Azure (Microsoft), email + password (TA only).
- **Supabase Postgres** is the system of record. Schema changes are SQL migrations in `supabase/migrations/` (Supabase CLI), never made in the dashboard.
- **Supabase Storage** holds files in private buckets; access is only through short-lived signed URLs issued by the API.
- Environments: `local` (Supabase CLI), `staging`, `production` — separate Supabase projects.

## Consequences
- The API verifies Supabase JWTs (JWKS) on every request.
- Row-Level Security is enabled on every table as a safety net (deny by default), even though the API is the only data client (ADR-006).
- Large interview recordings need Storage upload size limits raised and resumable/chunked uploads (see `architecture/STORAGE.md`).
- Data residency is tied to the Supabase project region. MVP uses one region; multi-region is post-MVP.

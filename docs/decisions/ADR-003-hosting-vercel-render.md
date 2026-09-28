# ADR-003: Vercel for the web app, Render for the API, worker and Redis

- **Status:** Accepted (environment list amended by ADR-019)
- **Date:** 2026-09-29

## Decision
- **Vercel** hosts `apps/web` (preview deployments per PR, production on `main`/`master`).
- **Render** hosts, defined in `render.yaml` (Infrastructure as Code):
  - `fasthyr-api` — Web Service running FastAPI (uvicorn).
  - `fasthyr-worker` — Background Worker running arq jobs and cron (ADR-009).
  - `fasthyr-redis` — Render Key Value (Redis-compatible) for the job queue and rate limits.
- Domains: `fasthyr.com` (marketing, apply, interview, demo) and `app.fasthyr.com` (TA app) both served by the one Next.js app; `api.fasthyr.com` → Render API.

## Consequences
- Live interview audio/video does **not** pass through Render: the browser connects to OpenAI Realtime directly over WebRTC with a short-lived token (ADR-007), and uploads recordings straight to Supabase Storage.
- CORS on the API allows only the two web origins per environment.
- Long-running work (screening, scoring, PDFs, transcription) never runs inside an API request; it is queued for the worker.

# ADR-009: Background jobs with arq and Redis on a Render worker

- **Status:** Accepted
- **Date:** 2026-09-29

## Decision
- Use **arq** (asyncio job queue for Python) backed by **Render Key Value (Redis)**.
- The worker runs from the same `apps/api` codebase (`python -m app.worker`).
- Jobs: résumé screening, interview plan generation, recording finalisation, transcription, scoring, integrity checks, PDF generation, email sending, Stripe follow-ups, data retention.
- Cron jobs (arq cron): open scheduled pipelines, close pipelines at `closes_at`, expire interview links, send reminders, expire credit batches, scheduled emails, retention purge.
- Jobs are **idempotent** (safe to retry) and keyed by entity ID; job state that users see (e.g. report generation progress) is stored in Postgres, not only in Redis.

## Consequences
- Redis is not a system of record; losing it loses only queued work, which cron sweepers re-enqueue from Postgres state.

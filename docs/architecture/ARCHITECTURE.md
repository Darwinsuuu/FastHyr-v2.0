# Architecture overview

## 1. System context

```
                 ┌──────────────────────── Browser ─────────────────────────┐
                 │  fasthyr.com (marketing, apply, interview, demo)          │
                 │  app.fasthyr.com (TA app)        — one Next.js app        │
                 └───┬──────────────┬───────────────┬───────────────┬───────┘
     Supabase Auth   │   REST/JSON  │  WebRTC audio │  signed URLs  │ Stripe.js
     (sign-in only)  │   (JWT)      │  + events     │  (upload/     │ (3-D Secure,
                     ▼              ▼               ▼   download)   ▼  card forms)
             ┌────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────┐  ┌────────┐
             │ Supabase   │  │ FastAPI API  │  │ OpenAI   │  │ Supabase     │  │ Stripe │
             │ Auth       │  │ (Render)     │◀▶│ Realtime │  │ Storage      │  │        │
             └────────────┘  └──┬───┬───┬───┘  └──────────┘  └──────▲───────┘  └───┬────┘
                                │   │   │ sideband control            │              │ webhooks
                                │   │   └─────────── enqueue ──┐      │              ▼
                                │   │                          ▼      │         FastAPI /webhooks
                                │   │                    ┌───────────┐│
                                │   └──── Postgres ─────▶│  Worker   ││
                                │      (Supabase DB)     │  (arq,    │┘  OpenAI text + transcription,
                                │                        │  Render)  │   Resend email, WeasyPrint PDFs,
                                ▼                        └─────┬─────┘   face checks (local)
                         Redis (Render Key Value) ◀────────────┘
```

- **Web (Next.js on Vercel):** renders marketing pages, the public apply page, the candidate interview, the demo and the TA app. Uses Supabase Auth for sessions and calls FastAPI for everything else (ADR-006).
- **API (FastAPI on Render):** the only component that reads/writes business data. Verifies Supabase JWTs, resolves workspace and role, enforces permissions, mints signed storage URLs and OpenAI Realtime client secrets, handles Stripe and Resend webhooks, enqueues jobs.
- **Worker (same Python codebase on Render):** runs every slow or scheduled task (ADR-009).
- **Supabase:** Auth, Postgres (system of record), Storage (private buckets).
- **OpenAI:** Realtime API for live interviews; Responses API and transcription for everything else (ADR-007).
- **Stripe:** subscriptions, one-time credit packs, invoices, customer portal (ADR-004).
- **Resend:** all outbound email (ADR-008).

## 2. Main flows

### Apply → screen → invite
1. Candidate opens `/apply/{ws}/{pipeline}?source=linkedin` → web fetches `GET /public/pipelines/{ws}/{slug}`.
2. Candidate signs in with Google/Microsoft (Supabase OAuth) → web calls `POST /candidate/applications/{pipeline_id}/upload-url` → uploads PDF directly to Storage.
3. `POST /candidate/applications` → API checks pipeline is live, consumes 1 credit (transaction), creates candidate + application (`processing_resume`), enqueues `screen_resume`.
4. Worker extracts + redacts text, scores with OpenAI, writes `resume_assessments` + `ai_decisions`, then either enqueues `plan_interview` + sends invitation, or schedules the rejection email.

### Interview
1. Candidate opens `/interview/{token}` → `GET /candidate/interviews/{token}` (must be the same Supabase user).
2. Device check in the browser; consent `POST …/consent`.
3. `POST …/session` → API builds instructions from the interview plan and creates an OpenAI Realtime client secret; returns it plus signed upload URLs for recording chunks.
4. Browser opens a WebRTC connection to OpenAI; the API attaches a sideband connection to control the session (time cap, wrap-up, end) and receive events.
5. Browser records and uploads chunks; heartbeat `POST …/heartbeat` every 15 s.
6. On end → `POST …/complete` → worker: finalise recording → transcribe → score → integrity checks → stage update → emails.

### Review
TA opens a candidate profile → API returns application, résumé assessment, assessment, transcript, flags and signed playback URL.

## 3. Cross-cutting
- **Tenancy & permissions:** `MULTI_TENANCY.md`, `SECURITY.md`.
- **Data model:** `DATABASE.md`. **Files:** `STORAGE.md`. **API contract:** `API.md`.
- **AI:** `AI_PIPELINE.md` (screening, planning, scoring, Ava), `MEDIA.md` (capture, Realtime, recording, transcription, integrity).
- **Money:** `BILLING.md`. **Email:** `NOTIFICATIONS.md`. **Environments & CI/CD:** `DEPLOYMENT.md`.

## 4. Repository layout (target)

```
FastHyr-v2.0/
├── AGENTS.md · CLAUDE.md · README.md · Makefile · render.yaml
├── apps/
│   ├── web/                     # Next.js (see FRONTEND.md)
│   │   └── AGENTS.md            # frontend-only rules
│   └── api/                     # FastAPI + worker (see BACKEND.md)
│       └── AGENTS.md            # backend-only rules
├── packages/
│   └── api-client/              # generated from FastAPI OpenAPI
├── supabase/
│   ├── config.toml
│   ├── migrations/              # SQL, source of truth for the schema
│   └── seed.sql
├── docs/
└── .github/workflows/
```

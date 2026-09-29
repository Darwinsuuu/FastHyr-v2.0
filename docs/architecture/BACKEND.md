# Backend (`apps/api`)

## 1. Structure
```
apps/api/
├── pyproject.toml · uv.lock · .env.example
├── app/
│   ├── main.py                  # FastAPI app factory, routers, middleware
│   ├── worker.py                # arq WorkerSettings (functions + cron)
│   ├── core/
│   │   ├── config.py            # pydantic-settings; all env vars
│   │   ├── db.py                # async engine/session
│   │   ├── auth.py              # Supabase JWT verification → CurrentUser
│   │   ├── context.py           # RequestContext: user, workspace, membership, departments
│   │   ├── permissions.py       # can(ctx, action, resource) — the matrix from SECURITY.md
│   │   ├── errors.py            # AppError hierarchy → problem+json responses
│   │   ├── ratelimit.py
│   │   └── logging.py
│   ├── models/                  # SQLAlchemy models (mirror supabase/migrations)
│   ├── repositories/            # ONLY place that builds queries; every method takes workspace_id
│   ├── services/                # business rules (pipelines, applications, credits, interviews, billing…)
│   ├── ai/                      # OpenAI wrappers, prompts/, schemas/, redaction, evaluation fixtures
│   ├── media/                   # recording finalise, transcription, frame sampling, face checks
│   ├── integrations/            # stripe_client, resend_client, storage (Supabase Storage)
│   ├── jobs/                    # arq job functions (thin: load → call service → save)
│   ├── emails/                  # Jinja2 layout, default templates, renderer
│   ├── pdf/                     # WeasyPrint templates for reports
│   └── api/
│       ├── deps.py              # Depends(): ctx, require(action)
│       └── routers/             # public.py, candidate.py, me.py, workspaces.py, pipelines.py, applications.py,
│                                # candidates.py, interviews.py, ava.py, templates.py, billing.py, analytics.py,
│                                # jobs.py, demo.py, webhooks_stripe.py, webhooks_resend.py, admin_compliance.py
└── tests/
    ├── unit/ · integration/ · tenancy/   # tenancy/: cross-workspace access tests for every endpoint
    └── ai_eval/                          # golden résumés/transcripts for prompt regression checks
```

## 2. Layering rules
1. **Routers** parse input, call `require(...)`, call one service method, return a response model. No SQL, no business logic.
2. **Services** hold business rules and transactions. They receive a `RequestContext` (or a system context for jobs) and call repositories and integrations.
3. **Repositories** are the only code that touches SQLAlchemy queries. Every read/write method requires `workspace_id` and filters by it; department scoping is applied here via `ctx.visible_department_ids`.
4. **Jobs** are thin wrappers: load IDs, call a service, commit. They must be idempotent.
5. **Integrations** wrap third-party SDKs so tests can swap in fakes.

## 3. Conventions
- **IDs:** UUID v7 (time-ordered) generated in the API.
- **Time:** store UTC `timestamptz`; convert using the workspace time zone only for display and business-day calculations.
- **Errors:** RFC 9457 `application/problem+json` with a stable `code` (e.g. `pipeline_locked`, `insufficient_free_credits`, `application_exists`). The web shows messages by `code`. Body: `type`, `title`, `status`, `code`, `request_id`, and `errors` (location and reason only, never the submitted value) for `validation_failed`. Codes in place since FND-004: `unauthenticated` (401), `workspace_required` (400), `not_a_member` (403), `forbidden` (403, role may not take the action), `email_not_verified` (403, from `VerifiedUserDep`, for creating or joining a workspace; AUTH-002), `not_found` (404, also for anything outside the caller's workspace or scope), `validation_failed` (422), `method_not_allowed` (405), `internal_error` (500).
- **Request IDs:** every response carries `X-Request-Id` (a valid incoming one is kept); logs include it. Error bodies repeat it so support can find the log line without any personal data.
- **Auth:** `core/auth.py` verifies Supabase access tokens (ES256/RS256) against the project JWKS, cached 10 minutes and refreshed on an unknown key ID; `exp`, `aud` and `iss` are required. Shared-secret (HS256) tokens are refused.
- **Context and permissions:** `api/deps.py` builds `RequestContext` (user, workspace, member, role, owner, department IDs) from `X-Workspace-Id`; `require(action)` checks `permissions.can()`, which returns the access width (`workspace`, `departments` or `shortlist`) repositories apply.
- **Pagination:** `?page=&per_page=` with `total` in the response (the design shows numbered pages).
- **Idempotency:** `Idempotency-Key` header on POSTs that spend money or credits (apply, buy credits, top-up).
- **Money:** integer cents + ISO currency.
- **Credits:** only `services/credits.py` changes balances, always inside a DB transaction with row locks (see `BILLING.md`).
- **AI:** only `app/ai/` calls OpenAI. Every call has a versioned prompt (`prompts/<name>@vN.md`), a JSON schema for output, and writes an `ai_calls` row (model, prompt version, tokens, latency, cost, entity).
- **Emails:** only `services/emails.py` sends/schedules email (never directly from a router).
- **Audit:** services call `audit.record(ctx, action, entity, data)` for actions listed in `SECURITY.md`.
- **Typing:** mypy strict on `app/`; Pydantic models for every request/response.
- **OpenAPI:** response models are complete so `packages/api-client` generation is lossless; `make api-client` regenerates.

## 4. Jobs catalogue
| Job | Trigger | Notes |
|---|---|---|
| `screen_resume(application_id)` | apply | extract → redact → score → decide → next job/email |
| `plan_interview(application_id)` | screen pass | creates `interview_plans`, then invitation email |
| `finalize_recording(interview_id)` | interview complete | remux chunks → single file, extract audio/frames |
| `transcribe_interview(interview_id)` | after finalize | authoritative transcript |
| `score_interview(interview_id)` | after transcribe | assessment + stage |
| `check_integrity(interview_id)` | after transcribe (if enabled) | flags |
| `send_email(message_id)` | scheduled time | render + Resend |
| `generate_report(job_id)` | TA request | candidate / pipelines report PDF |
| `stripe_event(event_id)` | webhook | grant credits etc. |
| cron `open_scheduled_pipelines` | every minute | |
| cron `close_due_pipelines` | every 5 min | releases reserves |
| cron `expire_interview_links` / `send_interview_reminders` / `nudge_unfinished` | every 10 min | |
| cron `expire_credit_batches` | hourly | ledger entries |
| cron `dispatch_scheduled_emails` | every minute | |
| cron `retention_purge` | daily | `compliance/PRIVACY.md` |
| cron `purge_demo_sessions` | hourly | |
| cron `requeue_stuck_work` | every 10 min | re-enqueue applications/interviews stuck in processing states |

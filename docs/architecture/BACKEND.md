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
│   ├── ai/                      # OpenAI wrappers, prompts/, schemas/, evaluation fixtures
│   ├── screening/               # résumé text extraction and redaction rules (no database; SCREEN-001)
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
- **Errors:** RFC 9457 `application/problem+json` with a stable `code` (e.g. `pipeline_locked`, `insufficient_free_credits`, `application_exists`). The web shows messages by `code`. Body: `type`, `title`, `status`, `code`, `request_id`, and `errors` (location and reason only, never the submitted value) for `validation_failed`. Codes in place since FND-004: `unauthenticated` (401), `workspace_required` (400), `not_a_member` (403), `forbidden` (403, role may not take the action), `email_not_verified` (403, from `VerifiedUserDep`, for creating or joining a workspace; AUTH-002), `not_found` (404, also for anything outside the caller's workspace or scope), `invite_not_found` (404), `invite_wrong_email` (403, checked before anything else about the invite), `invite_expired` (410), `invite_invalid` (410, revoked or used by someone else; AUTH-003), `already_a_member` (409, inviting someone who already has access; WS-004), `insufficient_free_credits` (409, reserve or top-up above free credits), `pipeline_not_accepting` (409, pipeline not live, reserve used up or no credits left; no credit used; BILL-002), `invalid_webhook_signature` (400, a webhook whose signature fails; FND-010), `notice_unknown` (422, a consent naming a notice id that was never released or is of another kind; COMP-002), `notice_outdated` (409, a consent to an older version of a notice; the page shows the current one; COMP-002), `candidate_sign_in_required` (403, a `/candidate/*` route called without a Google or Microsoft session; APPLY-003), `validation_failed` (422), `method_not_allowed` (405), `internal_error` (500).
- **Request IDs:** every response carries `X-Request-Id` (a valid incoming one is kept); logs include it. Error bodies repeat it so support can find the log line without any personal data.
- **Auth:** `core/auth.py` verifies Supabase access tokens (ES256/RS256) against the project JWKS, cached 10 minutes and refreshed on an unknown key ID; `exp`, `aud` and `iss` are required. Shared-secret (HS256) tokens are refused.
- **Context and permissions:** `api/deps.py` builds `RequestContext` (user, workspace, member, role, owner, department IDs) from `X-Workspace-Id`; `require(action)` checks `permissions.can()`, which returns the access width (`workspace`, `departments` or `shortlist`) repositories apply.
- **Pagination:** `?page=&per_page=` with `total` in the response (the design shows numbered pages).
- **Idempotency:** `Idempotency-Key` header on POSTs that spend money or credits (apply, buy credits, top-up).
- **Money:** integer cents + ISO currency.
- **Credits:** only `services/credits.py` changes balances, always inside a DB transaction with row locks (see `BILLING.md`).
- **Candidate notices (COMP-002):** consent texts are versioned files in `app/compliance/notices/` checked against `versions.lock`; records store the notice id through `services/consents.accept()` (`compliance/PRIVACY.md` §3).
- **AI:** only `app/ai/` calls OpenAI. Every call has a versioned prompt (`prompts/<name>@vN.md`), a JSON schema for output, and writes an `ai_calls` row (model, prompt version, tokens, latency, cost, entity).
- **Emails:** only `services/emails.py` sends/schedules email (never directly from a router).
- **Audit:** services call `audit.record(ctx, action, entity, data)` for actions listed in `SECURITY.md`.
- **Typing:** mypy strict on `app/`; Pydantic models for every request/response.
- **OpenAPI:** response models are complete so `packages/api-client` generation is lossless; `make api-client` regenerates.

## 4. Jobs catalogue
| Job | Trigger | Notes |
|---|---|---|
| `screen_resume(application_id)` | apply | extract → redact → score → decide; a pass queues `plan_interview`, a fail moves to `resume_not_match` and schedules the rejection (`services/post_screen.act()`, SCREEN-003) |
| `plan_interview(application_id)` | screen pass | creates `interview_plans` (INTV-001; after the last failed try the failure hook stores the plain skills plan), then `services/post_screen.act()`: stage `invited`, an `interviews` row with its link token, invitation email (SCREEN-003; the failure hook invites too, and its email goes with the next `dispatch_scheduled_emails` tick) |
| `run_realtime_session(workspace_id, attempt_id)` | `POST …/session` | holds the sideband to the attempt's Realtime call until it ends (INTV-004, `app/interview/sideband.py`): applies and guards the instructions, answers tool calls, wrap-up at 25 min, hangs up at the cap, logs the call's cost; timeout 35 min, a retry re-attaches without greeting again |
| `finalize_recording(interview_id)` | interview complete | remux chunks → single file, extract audio/frames; records each attempt's place in the recording and, once `ready`, queues `transcribe_interview` (INTV-008) |
| `transcribe_interview(workspace_id, interview_id)` | after finalize | authoritative transcript (INTV-008, `services/transcripts.py`): `audio.m4a` cut at silences into ≤ 10-minute pieces, diarised by `OPENAI_TRANSCRIBE_MODEL`, mapped to interviewer/candidate/other and topics from `interview_events`, stored in `transcript_segments`; 4 tries, then `transcript_status = failed`; timeout 20 min; `requeue_stuck_work` re-queues ready recordings still without one |
| `score_interview(interview_id)` | after transcribe | assessment + stage |
| `check_integrity(interview_id)` | after transcribe (if enabled) | flags |
| `send_email(message_id)` | scheduled time | sends the already-rendered row through Resend (Mailpit locally); FND-010 |
| `generate_report(job_id)` | TA request | candidate / pipelines report PDF |
| `stripe_event(event_id)` | webhook | grant credits etc. |
| cron `open_and_close_pipelines` | every minute | opens scheduled pipelines at `opens_at` and closes open ones at `closes_at` (releasing their unused reserve), one transaction per pipeline (PIPE-001) |
| cron `expire_interview_links` | every 10 min | moves live links past `expires_at` that were never started or were left unfinished to `expired` with their drop-off reason (`link_expired`, else the reason they had) and cancels their waiting reminder and finish emails; a link with a running attempt waits for the watchdog (INTV-007). Reminders and "Finish your interview" are scheduled emails, not crons (NOTIFICATIONS.md §1) |
| cron `end_overdue_attempts` | every minute | ends live interview attempts past their share of the cap or without a heartbeat for 60 s and hangs up their calls (INTV-004) |
| cron `expire_credit_batches` | hourly | ledger entries |
| cron `dispatch_scheduled_emails` | every minute | queues the send of every `scheduled` email whose time has come, keyed by email ID; also picks up enqueues Redis lost (MSG-003) |
| cron `retention_purge` | daily | `compliance/PRIVACY.md` |
| cron `remove_storage_orphans` | daily 03:25 UTC | deletes temp uploads (`tmp/`) and demo files older than 24 h (FND-011); later tasks add files whose rows are gone |
| cron `purge_demo_sessions` | hourly | |
| cron `requeue_stuck_work` | every 10 min | re-enqueue work stuck in a waiting state: report jobs still queued after 10 min (FND-008); résumé screens and interview plans (SCREEN-001, INTV-001); screened applications still `processing_resume` 10 min after the screen (SCREEN-003: a fail re-runs `screen_resume`, a pass with its plan re-runs `plan_interview`; both skip finished steps); ready recordings whose transcript is still `none`/`processing` 10 min after the interview completed (INTV-008); applications/interviews in processing states (their tasks) |

### How jobs work (FND-008)
- **Worker:** `app/worker.py` `WorkerSettings` lists every function and cron; run it with `python -m app.worker` (`make worker` locally). Crons run at different minutes of the hour (`expire_credit_batches` :05, `expire_invites` :15; daily `remove_storage_orphans` 03:25 UTC) and are `unique`, so several workers run each tick once.
- **Job bodies** live in `app/jobs/` and are wrapped by `@job(retry=RetryPolicy(...), on_failure=...)` from `app/jobs/framework.py`: a fresh session per try (the body commits), rollback on error, retry after `base_delay * 2^(try-1)` (capped), and after the last try `on_failure` records the error in Postgres. Crons use `NO_RETRY`: the next tick does the work again.
- **Enqueue** with `JobQueue.enqueue(function, *args, key=entity_id)` (`app/jobs/queue.py`, `JobQueueDep` in routers, `run.queue` in jobs) **after** committing the rows the job reads. `key` makes it idempotent: the same function and key can't be queued twice at once. Bodies still check their row's state first, so a retry or a sweeper re-enqueue never repeats finished work.
- **Progress people wait on** lives in `report_jobs`: `services/jobs.start_report_job()` inserts, commits and enqueues; the body uses `Progress` (`start()` claims it, `step(n)` commits each step and returns False once cancelled, `done()`); `GET /v1/jobs/{id}` reads it. Add a report kind to `JOB_FUNCTIONS` so the sweeper can re-queue it.
- Redis keeps no results (`keep_result = 0`); a lost Redis loses only queued work, which `requeue_stuck_work` rebuilds from Postgres.

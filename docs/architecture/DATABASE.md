# Database (Supabase Postgres)

Source of truth: SQL migrations in `supabase/migrations/`. This document is the design; if they disagree, fix one of them in the same PR.

Conventions: `id uuid primary key` (UUID v7 from the API), `created_at`/`updated_at timestamptz default now()`, snake_case, enums as Postgres `text` + `check` constraints (easier to evolve), JSONB only for AI outputs and snapshots. Every tenant table has `workspace_id` (see `MULTI_TENANCY.md`); parents referenced by other tenant tables carry `unique (workspace_id, id)` so children use composite FKs. RLS enabled everywhere with no client policies; the API connects as `fasthyr_api`. Append-only tables (`audit_log`, `credit_ledger`, `ai_decisions`) grant the API role only `select, insert` and have a trigger rejecting updates and deletes. SQLAlchemy models in `apps/api/app/models/` mirror the migrations; `make db-drift` fails when they differ (check constraints and triggers live only in SQL).

## 1. Entity overview

```
auth.users ─1:1─ profiles
workspaces ─┬─ company_profiles (1:1)
            ├─ workspace_members ─< member_departments >─ departments
            ├─ invites
            ├─ pipelines ─< applications >─ candidates
            │                  ├─ resume_assessments (1:1)
            │                  ├─ interview_plans (1:1)
            │                  ├─ interviews ─< interview_attempts, recording_chunks, transcript_segments, integrity_flags
            │                  ├─ assessments (1:1 per completed interview)
            │                  ├─ human_review_requests
            │                  └─ email_messages
            ├─ email_templates ─< email_template_versions
            ├─ ava_threads ─< ava_messages
            ├─ report_jobs
            ├─ subscriptions · credit_batches · credit_ledger · stripe_invoices
            ├─ ai_decisions · ai_calls · audit_log · deletion_requests
demo_sessions · contact_requests · stripe_events (no tenant)
```

## 2. Tables

### Identity and workspaces
**profiles** — `id` (= auth.users.id), `full_name`, `avatar_url`, `email`, `last_workspace_id`, `created_at`. Created by a trigger when an `auth.users` row is inserted, with name and avatar from the Google/Microsoft metadata. `email` is a lowercase copy of `auth.users.email` (for the members list; the API can't read the `auth` schema), kept current by a second trigger on email change.

**workspaces** — `id`, `name`, `slug` (unique, used in apply links), `owner_id`, `timezone` (default from company profile), `stripe_customer_id`, `trial_granted_at`, `created_at`.

**company_profiles** — `workspace_id` PK, `company_name`, `logo_path`, `banner_path`, `website`, `industry`, `company_size`, `hq_country`, `timezone`, `about` (≤600), `careers_url`, `updated_by`, `updated_at`.

**departments** — `id`, `workspace_id`, `name` (unique per workspace, case-insensitive; "no department" reserved), `description`, `created_at`. Deleting one cascades to `member_departments`; the service also removes its ID from pending `invites.department_ids` and first moves its pipelines to No department (`pipelines.department_id` has a composite FK with no ON DELETE action).

**workspace_members** — `id`, `workspace_id`, `user_id`, `role` (`admin|recruiter|hiring_manager`), `is_owner`, `status` (`active|removed`), `last_active_at` (written by the request context at most every 5 minutes), `created_at`. Unique `(workspace_id, user_id)`; one owner per workspace, and the owner is an Admin.

**member_departments** — `workspace_id`, `member_id`, `department_id`. PK `(member_id, department_id)`.

**invites** — `id`, `workspace_id`, `email`, `role`, `department_ids uuid[]`, `code` (short, e.g. `AB12-CD34`, unique), `token_hash`, `invited_by`, `status` (`pending|accepted|revoked|expired`), `expires_at` (+7 days), `accepted_by`, `created_at`. Email stored lowercase; one pending invite per email per workspace (resend rotates `code` and `token_hash` on the same row).

### Pipelines
**pipelines** (BILL-002 created the table with the credit columns, `status`, `created_at` and `updated_at`; PIPE-001 adds the rest)
| Column | Notes |
|---|---|
| `id`, `workspace_id`, `department_id` (nullable = No department), `owner_id` (member who created) | |
| `slug` | unique per workspace, fixed after publish |
| `title`, `employment_type` (`full_time|part_time|contract|internship`), `work_setup` (`on_site|hybrid|remote`), `location`, `jd_text` | Role |
| `must_haves text[]` (≥3), `nice_to_haves text[]`, `open_to text[]` (`fresh_grads|career_changers|returners|no_degree|step_up|relocating`), `resume_pass_bar int` (0–100, default 60) | Screening (ADR-013) |
| `interview_format` (`video_voice|voice_only`), `tone` (`warm|professional|direct`), `seniority` (`entry|mid|senior|lead`), `skills_to_probe text[]` (≥3), `link_expiry_days` (3/5/7/14), `reminder_enabled`, `integrity_enabled` | AI interview |
| `weight_technical`, `weight_communication`, `weight_culture` (sum = 100, check), `pass_mark` (0–100, default 70), `email_resume_reject`, `email_post_interview` | Scoring |
| `open_mode` (`now|scheduled`), `opens_at`, `duration_days` (30/60/90/120), `closes_at` | Schedule |
| `credits_reserved int`, `credits_used int` | Reserve (see BILLING.md); check `credits_used between 0 and credits_reserved` |
| `status` (`draft|scheduled|live|paused|paused_no_credits|closed|cancelled`), `closed_reason` (`schedule|manual`), `archived_at`, `published_at`, `published_by`, `locked_at`, `duplicated_from_id` | Lifecycle (WORKFLOW.md §2) |
A trigger rejects updates to setup columns when `locked_at is not null`.

### Candidates and applications
**candidates** — `id`, `workspace_id`, `auth_user_id`, `email`, `full_name`, `phone_country_code`, `phone`, `city`, `profile_url`, `first_applied_at`, `last_activity_at`, `deleted_at`. Unique `(workspace_id, auth_user_id)`.

**applications**
| Column | Notes |
|---|---|
| `id`, `workspace_id`, `pipeline_id`, `candidate_id` | unique `(pipeline_id, candidate_id)` |
| `source` (`linkedin|jobstreet|indeed|kalibrr|glassdoor|facebook|careers|other|direct`) | from `?source=` |
| `resume_path`, `resume_filename`, `resume_pages`, `resume_bytes` | |
| `consent_version`, `consent_at`, `consent_ip_hash` | FR-COMP-01 |
| `stage` (WORKFLOW.md §3), `stage_changed_at` | |
| `resume_status` (`pending|done|unreadable|error`) | |
| `fit` (`strong|good|null`), `overall_score` (denormalised for lists) | |
| `has_open_flags bool`, `review_requested bool` | overlays |
| `rejected_reason`, `rejected_by`, `rejected_at`, `advanced_note`, `advanced_by`, `advanced_at` | ADR-017 |
| `credit_ledger_id` | the consumption entry |
| `applied_at` | |

**resume_assessments** — `application_id` PK, `workspace_id`, `score`, `breakdown jsonb` (must_haves, nice_to_haves, experience, skill_depth: score, weight, detail), `must_have_results jsonb` (criterion, met, evidence quote), `nice_to_have_results jsonb`, `impact jsonb`, `claims jsonb` (requirement, type, found, strength 1–3), `experience_timeline jsonb`, `career_snapshot jsonb`, `redacted_text` (encrypted column or storage path), `passed bool`, `model`, `prompt_version`, `screened_at`, `duration_ms`.

**interview_plans** — `application_id` PK, `workspace_id`, `topics jsonb` (ordered: title, goal, seeds[{question, resume_quote}], skills), `claims_to_verify jsonb`, `instructions_version`, `model`, `prompt_version`, `created_at`.

### Interviews
**interviews** — `id`, `workspace_id`, `application_id`, `token_hash` (link token), `format`, `status` (`not_started|in_progress|abandoned|completed|expired`), `drop_reason` (`link_expired|left_unfinished|technical_issue|null`), `invited_at`, `expires_at`, `reminder_sent_at`, `started_at`, `completed_at`, `talk_seconds`, `consent_version`, `consent_at`, `biometric_consent bool`, `recording_path` (final), `recording_status` (`none|uploading|finalizing|ready|failed`), `duration_seconds`, `feedback_rating` (1–5), `feedback_comment`, `superseded_by` (re-invite).

**interview_attempts** — `id`, `workspace_id`, `interview_id`, `realtime_session_id`, `started_at`, `ended_at`, `end_reason` (`candidate_ended|wrap_up|time_cap|disconnect|error`), `talk_seconds`.

**recording_chunks** — `id`, `workspace_id`, `interview_id`, `attempt_id`, `seq`, `path`, `bytes`, `uploaded_at`. Unique `(attempt_id, seq)`.

**transcript_segments** — `id`, `workspace_id`, `interview_id`, `start_ms`, `end_ms`, `speaker` (`interviewer|candidate|other`), `text`, `topic_index`. Full-text index for transcript search.

**assessments** — `id`, `workspace_id`, `application_id`, `interview_id`, `overall_score`, `criteria jsonb` (technical/communication/culture: score, weight, points, signals[{name, score}], evidence[{quote, start_ms | resume_ref, source_label}], held_back), `topics jsonb` (title, start_ms, questions, follow_ups, score), `summary jsonb` (text with numbered refs, refs[]), `strengths jsonb`, `probes jsonb`, `claims_checked jsonb`, `answer_stats jsonb`, `rubric_snapshot jsonb` (weights + pass mark at scoring time), `passed bool`, `model`, `prompt_version`, `created_at`.

**integrity_flags** — `id`, `workspace_id`, `interview_id`, `application_id`, `type` (`different_face|no_face|second_voice|read_aloud|unusual_timing`), `start_ms`, `end_ms`, `detail`, `confidence`, `status` (`open|no_concern|concern_confirmed`), `resolved_by`, `resolved_at`, `resolution_note`.

**human_review_requests** — `id`, `workspace_id`, `application_id`, `decision_type` (`resume|interview`), `token_hash`, `candidate_message`, `status` (`open|upheld|overridden`), `resolved_by`, `resolved_at`, `resolution_note`, `created_at`.

### Messaging
**email_templates** — `id`, `workspace_id`, `key` (`interview_invitation|interview_reminder|finish_interview|next_stage|reject_resume|reject_interview|interview_received|role_closed|review_received`), `subject`, `body_html`, `is_default bool`, `updated_by`, `updated_at`. Unique `(workspace_id, key)`.

**email_template_versions** — `id`, `workspace_id`, `template_id`, `subject`, `body_html`, `created_by`, `created_at`, `note` (e.g. "Reset to default").

**email_messages** — `id`, `workspace_id` (null only for the contact form), `application_id` (nullable), `template_key` (workspace template key, or a system key such as `member_invite`, `test`), `to_email`, `from_name`, `subject_rendered`, `html_rendered`, `text_rendered` (rendered when queued, FND-010), `scheduled_for`, `status` (`scheduled|cancelled|sending|sent|delivered|bounced|complained|failed`), `provider_message_id` (unique), `cancel_reason`, `sent_at`, `status_updated_at`, `error` (stable code: `provider_rejected`, `provider_unavailable`, `send_failed`), `created_at`.

### Ava and reports
**ava_threads** — `id`, `workspace_id`, `member_id`, `scope` (`pipeline|workspace`), `pipeline_id`, `created_at`.
**ava_messages** — `id`, `workspace_id`, `thread_id`, `role` (`user|assistant`), `content jsonb` (paras, table, bullets, note, sources[]), `refused bool`, `model`, `created_at`.
**report_jobs** — `id`, `workspace_id`, `requested_by`, `kind` (`candidate_report|pipelines_report|resume_download|sample`; `sample` is the local-only demo job, FND-008), `params jsonb`, `status` (`queued|running|done|failed|cancelled`), `step`, `steps_total`, `file_path`, `error` (stable code, never a message), `created_at`, `finished_at`. Only the member in `requested_by` sees a job. Redis only queues the work; this row is the state people see (ADR-009).

### Billing
**subscriptions** — `workspace_id` PK, `stripe_subscription_id`, `plan` (`starter|growth|scale`), `status` (Stripe status), `current_period_start`, `current_period_end`, `pending_plan`, `cancel_at_period_end`, `default_payment_method_brand`, `default_payment_method_last4`, `default_payment_method_exp`.

**credit_batches** — `id`, `workspace_id`, `kind` (`trial|plan|extra`), `amount`, `remaining`, `added_at`, `expires_at`, `stripe_invoice_id`, `note`. Check `remaining between 0 and amount`; at most one `trial` batch per workspace (partial unique index).

**credit_ledger** (append-only) — `id`, `workspace_id`, `kind` (`grant_trial|grant_plan|purchase|consume|reserve|release|top_up|expire|adjust`), `amount` (signed, balance change; 0 for reserve moves), `reserve_change` (signed), `pipeline_id`, `application_id`, `batch_id`, `balance_after` (unexpired balance after the change), `actor_id` (no FK), `created_at`. Composite FKs to `pipelines` and `credit_batches`; `application_id` gets its FK in APPLY-003. The ledger's `amount` always sums to the batches' `remaining`.

**stripe_invoices** (cache) — `id` (Stripe ID), `workspace_id`, `number`, `kind` (`plan|credits`), `description`, `amount_cents`, `currency`, `status` (`paid|open|failed|void`), `hosted_url`, `pdf_url`, `created_at`.

**billing_details** — `workspace_id` PK, `company_legal_name`, `billing_email`, `address jsonb`, `tax_id` (synced to Stripe customer).

### Compliance and ops
**ai_decisions** (append-only) — `id`, `workspace_id`, `application_id`, `type` (`resume_screen|interview_score|integrity_flag`), `outcome`, `score`, `threshold`, `model`, `prompt_version`, `input_ref`, `output jsonb`, `created_at`.
**ai_calls** — `id`, `workspace_id` (nullable), `purpose`, `entity_id` (no FK), `model`, `prompt_version` (`<name>@v<N>`), `input_tokens`, `output_tokens`, `audio_seconds`, `cost_usd` (null when the model has no price in `OPENAI_PRICES`), `latency_ms`, `status` (`ok|invalid_output|error`), `created_at`. One row per try, written in its own transaction by `app/ai/` (FND-013); never prompt or output text.
**audit_log** (append-only) — `id`, `workspace_id`, `actor_id` (no FK, null for system actions), `action`, `entity_type`, `entity_id`, `data jsonb`, `created_at`.
**deletion_requests** — `id`, `workspace_id`, `candidate_id`, `requested_by`, `reason`, `status`, `completed_at` (keeps only this minimal record after deletion).
**demo_sessions** — `id`, `ip_hash`, `jd_text`, `resume_text` (redacted), `settings jsonb`, `status`, `talk_seconds`, `created_at`, `expires_at` (+24 h hard delete).
**contact_requests** — `id`, `name`, `email`, `company`, `message`, `ip_hash`, `created_at`.
**stripe_events** — `id` (Stripe event ID, PK for idempotency), `type`, `payload jsonb`, `processed_at`, `error`.

## 3. Key indexes
- `applications (workspace_id, pipeline_id, stage)`, `(workspace_id, candidate_id)`, `(pipeline_id, applied_at)`.
- `pipelines (workspace_id, status)`, `(workspace_id, department_id)`, unique `(workspace_id, slug)`.
- `interviews (status, expires_at)` for cron; `email_messages (status, scheduled_for)`.
- `credit_batches (workspace_id, expires_at) where remaining > 0`.
- `transcript_segments` GIN on `to_tsvector('english', text)`.

## 4. Analytics
Dashboards read from SQL views (`v_pipeline_funnel`, `v_source_stats`, `v_dropoff_reasons`, `v_time_to_screen`) over `applications`/`interviews`. If they get slow, convert to materialised views refreshed by cron — not in MVP unless measured.

## 5. Seed data
`supabase/seed.sql` creates a demo workspace ("Acme Talent") with the departments, members, pipelines and sample candidates shown in the design, so every screen can be built against realistic data locally.

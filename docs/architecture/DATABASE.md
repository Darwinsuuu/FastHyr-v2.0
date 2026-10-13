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
            │                  ├─ resume_texts (1:1, redacted)
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
**pipelines** (BILL-002 created the table with the credit columns, `status`, `created_at` and `updated_at`; PIPE-001 added the rest. Setup columns are nullable because a draft saves at any wizard step; publishing checks the setup is complete)
| Column | Notes |
|---|---|
| `id`, `workspace_id`, `department_id` (nullable = No department), `owner_id` (workspace member who created it) | |
| `slug` | set on publish from the title (`-2`, `-3`… when taken), unique per workspace, fixed after publish; null on drafts |
| `title`, `employment_type` (`full_time|part_time|contract|internship`), `work_setup` (`on_site|hybrid|remote`), `location`, `jd_text` | Role |
| `must_haves text[]` (≥3), `nice_to_haves text[]`, `open_to text[]` (`fresh_grads|career_changers|returners|no_degree|step_up|relocating`), `resume_pass_bar int` (0–100, default 60) | Screening (ADR-013) |
| `interview_format` (`video_voice|voice_only`), `tone` (`warm|professional|direct`), `seniority` (`entry|mid|senior|lead`), `skills_to_probe text[]` (≥3), `link_expiry_days` (3/5/7/14), `reminder_enabled`, `integrity_enabled` | AI interview |
| `weight_technical`, `weight_communication`, `weight_culture` (sum = 100, check), `pass_mark` (0–100, default 70), `email_resume_reject`, `email_post_interview` | Scoring |
| `open_mode` (`now|scheduled`), `opens_at`, `duration_days` (30/60/90/120), `closes_at` (= when it opens + duration), `credits_to_reserve` (the wizard's reserve, min 10, steps of 10; publish reserves it) | Schedule |
| `credits_reserved int`, `credits_used int` | Reserve (see BILLING.md); check `credits_used between 0 and credits_reserved` |
| `status` (`draft|scheduled|live|paused|paused_no_credits|closed|cancelled`), `closed_reason` (`schedule|manual`, only on closed), `archived_at` (closed/cancelled only), `ended_at` (when it closed or was cancelled, closed/cancelled only; PIPE-004 shows "Closed 2 Sep" and sorts the Closed tab by it), `published_at`, `published_by` (member), `locked_at`, `duplicated_from_id` | Lifecycle (WORKFLOW.md §2) |
The `pipelines_lock_setup` trigger rejects changes to the Role, AI interview, Scoring and Schedule columns once `locked_at` is set (`department_id` may still become null, for department deletion), and any slug change after publish. Checks: enums and ranges, weights total 100 when set, `published_at`/`slug` set exactly when past draft.

### Candidates and applications
**candidates** — `id`, `workspace_id`, `auth_user_id`, `email`, `full_name`, `phone_country_code`, `phone`, `city`, `profile_url`, `first_applied_at`, `last_activity_at`, `email_undeliverable_at` (set by a hard bounce, MSG-003), `deleted_at`. Unique `(workspace_id, auth_user_id)`. Created on the first application to the workspace (APPLY-003); later applications keep the details sent last. `auth_user_id` has no FK, so deleting a sign-in account never touches the employer's records.

**applications**
| Column | Notes |
|---|---|
| `id`, `workspace_id`, `pipeline_id`, `candidate_id` | unique `(pipeline_id, candidate_id)` |
| `source` (`linkedin|jobstreet|indeed|kalibrr|glassdoor|facebook|careers|other|direct`) | from `?source=` |
| `resume_path`, `resume_filename`, `resume_pages`, `resume_bytes` | |
| `consent_version`, `consent_at`, `consent_ip_hash` | FR-COMP-01; the notice id (`apply@v1`); the IP only as an HMAC-SHA256 keyed from the service key (`services/applications.consent_ip_hash()`) |
| `stage` (WORKFLOW.md §3), `stage_changed_at` | |
| `resume_status` (`pending|done|unreadable|error`) | |
| `fit` (`strong|good|null`), `overall_score` (denormalised for lists) | written with the interview assessment (`services/scoring.py`, PIPE-008) |
| `has_open_flags bool`, `review_requested bool` | overlays; `has_open_flags` set when the integrity checks store an open flag (`services/integrity.py`), cleared when the last open flag is reviewed (`services/integrity_reviews.py`, ASMT-003); `review_requested` set by a human review request and cleared when it is resolved (`services/review_requests.py`, ASMT-008) |
| `rejected_reason`, `rejected_by`, `rejected_at`, `advanced_note`, `advanced_by`, `advanced_at` | ADR-017 |
| `credit_ledger_id` | the consumption entry |
| `applied_at` | |

**resume_texts** (SCREEN-001) — `application_id` PK (FK to the application, deleted with it), `workspace_id`, `redacted_text` (the only résumé text any AI step sees; the original text is never stored, the PDF stays the original), `characters` (non-space characters extracted), `pages`, `column_pages` (pages read as two columns), `masked jsonb` (counts per mask kind, never the hidden text), `redaction_version` (`rules@v2+resume_redaction@v1`; rules@v2 also masks school names in the Education section), `created_at`. Written once by `services/screening.py`; an unreadable résumé gets no row.

**resume_assessments** (SCREEN-002) — `application_id` PK (deleted with the application), `workspace_id`, `score` (0–100, computed in code), `breakdown jsonb` (must_haves, nice_to_haves, experience, skill_depth: score, weight, points, detail; a part with no criteria is left out and its weight redistributed), `must_have_results jsonb` (criterion, met, evidence quote, strength 0–3, waived, note), `nice_to_have_results jsonb` (criterion, found, where, evidence quote), `impact jsonb`, `claims jsonb` (requirement, type, found, strength 1–3), `experience_timeline jsonb` (employer, title, start/end year, current, relevant), `career_snapshot jsonb` (total years, companies, average years per role, promotions), `pass_bar` (the bar the decision used), `passed bool`, `model`, `prompt_version`, `screened_at`, `duration_ms` (from applying to the decision). Written once by `services/screening.py`, with its `ai_decisions` row and `resume_status = done`, in one transaction.

**interview_plans** (INTV-001) — `application_id` PK (deleted with the application), `workspace_id`, `topics jsonb` (in interview order: kind `warm_up` first, `skills` topics, `candidate_questions` last; title, goal, skills (copied from the pipeline's skills to probe), seeds[{question, resume_quote}] with quotes copied from the redacted résumé or ""), `claims_to_verify jsonb` (claim, resume_quote, skill), `source` (`ai`, or `fallback` for the plain skills plan stored when the model can't give a usable one), `instructions_version` (the live interviewer instructions it was used with, set by INTV-004), `model` (`none` for a fallback), `prompt_version` (`interview_plan@v1` or `interview_plan_fallback@v1`), `created_at`. Written once by `services/interviews.py`.

### Interviews
**interviews** (created by SCREEN-003 with the invitation; the interview tasks fill the rest) — `id`, `workspace_id`, `application_id`, `token_hash` (SHA-256 of the link token, unique; the link is `{SITE_URL}/interview/{token}`), `format`, `status` (`not_started|in_progress|abandoned|completed|expired`), `drop_reason` (`link_expired|left_unfinished|technical_issue|null`), `invited_at`, `expires_at`, `reminder_sent_at`, `started_at`, `completed_at`, `talk_seconds`, `consent_version`, `consent_at`, `biometric_consent_version` (null = not given; the biometric notice id, COMP-002), `recording_path` (final), `recording_status` (`none|uploading|finalizing|ready|failed`), `duration_seconds`, `transcript_status` (`none|processing|ready|failed`, INTV-008), `transcribed_at`, `feedback_rating` (1–5), `feedback_comment`, `superseded_by` (re-invite; the reference is checked at commit, so a re-invite points the old row at the new one before inserting it, INTV-007). `drop_reason` describes a live, unfinished interview: `left_unfinished` while it is abandoned (cleared when a new attempt starts), `technical_issue` after three failed connects, `link_expired` when it expired never started; completing clears it. `reminder_sent_at` is set when the reminder email is sent. One live interview per application (unique `application_id` where `superseded_by` is null). `expires_at` is the end of the day (23:59:59 in the workspace time zone) `link_expiry_days` after the invitation.

**interview_attempts** (INTV-004) — `id`, `workspace_id`, `interview_id` (deleted with it), `realtime_session_id` (the OpenAI call id), `started_at`, `connected_at` (first heartbeat saying the connection is up; null = never connected), `last_seen_at` (last heartbeat), `ended_at`, `end_reason` (`candidate_ended|wrap_up|time_cap|disconnect|error`; set exactly when `ended_at` is), `seconds_allowed` (what was left of the 30-minute cap at the start: the attempt ends at `started_at + seconds_allowed`), `talk_seconds` (≤ `seconds_allowed`, server clock), `resume_from` (0-based plan topic it started from), `topic_index` (furthest topic the interviewer reached), `wrap_up_sent_at`, `recording_type`, `recording_stopped_at` (INTV-006). `interviews.talk_seconds` is the sum over attempts. Written by `services/interview_sessions.py` and the sideband job.

**recording_chunks** (INTV-006) — `id`, `workspace_id`, `interview_id` (deleted with it), `attempt_id`, `seq` (0-based within the attempt), `path`, `bytes` (as Storage reports it), `uploaded_at` (when it was registered). Unique `(attempt_id, seq)`. Deleted once the recording is ready. `interview_attempts` also has `recording_type` (`webm|mp4`, fixed by the attempt's first chunk URL request) and `recording_stopped_at` (the browser registered the attempt's last chunk). Written by `services/recordings.py`.

**interview_events** (INTV-008) — `id`, `workspace_id`, `interview_id` (deleted with it), `attempt_id`, `kind` (`ai_speech|topic`), `at` (server clock: the interviewer's audio started, or `set_topic` was accepted), `ended_at` (`ai_speech`: its audio stopped; null if the call ended first), `ref` (`ai_speech`: the Realtime response id, unique per attempt), `text` (`ai_speech`: the interviewer's own words; nothing the candidate says is stored), `topic_index` (`topic`: 0-based), `created_at`. Written by the sideband (`app/interview/sideband.py`); the transcript job reads it to tell the interviewer's voice apart and to place lines in topics. `interview_attempts` also has `recording_offset_ms` and `recording_ms` (where the attempt sits in the final recording; null = left out), written by `finalize_recording`.

**transcript_segments** (INTV-008) — `id`, `workspace_id`, `interview_id` (deleted with it), `seq` (0-based order, unique per interview), `start_ms`, `end_ms` (in the final recording), `speaker` (`interviewer|candidate|other`), `text`, `topic_index` (0-based plan topic; null when no attempt is placed in the recording). Full-text index for transcript search. Replaced whole by the `transcribe_interview` job (`services/transcripts.py`); `interviews.transcript_status` (`none|processing|ready|failed`) and `transcribed_at` say where it is.

**assessments** (ASMT-001) — `id`, `workspace_id`, `application_id` (deleted with it), `interview_id` (unique: one per completed interview), `overall_score` (Σ score × weight, rounded half up, computed in code), `criteria jsonb` (technical/communication/culture: score, weight, points, signals[{name, score}], evidence[{source `interview|resume`, quote, start_ms (interview only), source_label}] with 2–4 items each, every quote checked word for word against its candidate turn or the redacted résumé, held_back), `topics jsonb` (index, title, start_ms, questions, follow_ups, score; the plan topics the interview reached, score null when the candidate said nothing in it), `summary jsonb` (text with [n] refs, refs[] in the evidence form), `strengths jsonb` and `probes jsonb` ([{title, reason}]), `claims_checked jsonb` (the résumé screen's claims: requirement, type, found, strength, status `confirmed|partly_confirmed|not_covered|probe_next_round`, start_ms), `answer_stats jsonb` (from transcript timings: answers, avg_answer_ms, avg_response_delay_ms, candidate_talk_ms, interviewer_talk_ms, talk_time_pct; questions, follow_ups and candidate_questions counted from the model's turn labels), `rubric_snapshot jsonb` (weights + pass mark at scoring time), `passed bool` (overall ≥ pass mark), `fit` (`strong_fit|good_fit|null`, ADR-011), `model`, `prompt_version`, `created_at`. Written once by `services/scoring.py` with its `ai_decisions` row and `interviews.assessment_status = ready` (`none|ready|failed`; `failed` = the scoring job gave up or the transcript has no candidate speech) in one transaction.

**integrity_flags** (ASMT-002) — `id`, `workspace_id`, `interview_id`, `application_id` (deleted with it), `type` (`different_face|no_face|second_voice|read_aloud|unusual_timing`), `start_ms`, `end_ms` (on the recording's clock), `detail jsonb` (numbers the flag was raised on: seconds, samples, similarity, delays against the session baseline; the model's one-sentence rationale for `read_aloud`; never an embedding or transcript text), `confidence numeric(3,2)` (0–1), `status` (`open|no_concern|concern_confirmed`; `resolved_at` set exactly when not open), `resolved_by`, `resolved_at`, `resolution_note`, `created_at`. Created only by `services/integrity.py`, each with its `ai_decisions` row; resolved by a person through `services/integrity_reviews.py` (ASMT-003; `resolved_by` the reviewer, `resolution_note` required for `concern_confirmed`). `interviews.integrity_status` (`none|ready|off|failed`; `off` = the pipeline's toggle was off, nothing ran), `integrity_checks jsonb` (`face`: `ran|no_consent|voice_only|no_video`; `second_voice`: `ran`; `timing` and `read_aloud`: `ran|too_short`, read_aloud also `failed`) and `integrity_checked_at` say where the checks are.

**review_links** (SCREEN-003) — `id`, `workspace_id`, `application_id` (deleted with it), `decision_type` (`resume|interview`), `token_hash` (SHA-256 of the token in `{SITE_URL}/review-request/{token}`, unique), `expires_at` (30 days after the rejection email goes out), `requested_at` (when the candidate used it, ASMT-008; a TA rejection that gives the link a new token clears it), `created_at`. One per application and decision type; made with every automated rejection email (ADR-015).

**human_review_requests** (ASMT-008) — `id`, `workspace_id`, `application_id` (deleted with it), `decision_type` (`resume|interview`), `review_link_id` (the link the request came through), `candidate_message` (≤ 1,000), `status` (`open|upheld|overridden`), `resolved_by` (workspace member ID), `resolved_at`, `resolution_note` (required to resolve, ≤ 1,000), `created_at`. At most one open request per application; `applications.review_requested` follows it. Written only by `services/review_requests.py`.

### Messaging
**email_templates** — `id`, `workspace_id`, `key` (`interview_invitation|interview_reminder|finish_interview|next_stage|reject_resume|reject_interview|interview_received|role_closed|review_received`), `subject` (1–200 characters), `body_html` (sanitised), `is_default bool` (true until someone saves their own wording), `updated_by` (null while default), `updated_at`. Unique `(workspace_id, key)`. Defaults come from `app/emails/defaults.py` (MSG-001).

**email_template_versions** — `id`, `workspace_id`, `template_id`, `subject`, `body_html`, `created_by`, `created_at`, `note` (e.g. "Reset to default"). One row per save; deleted with its template.

**email_messages** — `id`, `workspace_id` (null only for the contact form), `application_id` (nullable), `template_key` (workspace template key, or a system key such as `member_invite`, `test`), `to_email`, `from_name`, `subject_rendered`, `html_rendered`, `text_rendered` (rendered when queued, FND-010), `scheduled_for`, `application_stage` (the stage a candidate email was written for; it is cancelled if the stage moves, MSG-003), `dedupe_key` (unique while not cancelled), `status` (`held|scheduled|cancelled|sending|sent|delivered|bounced|complained|failed`; `held` = written but waiting for an event to schedule it, never dispatched: the "Finish your interview" email, INTV-007), `provider_message_id` (unique), `cancel_reason` (`stage_changed`, `link_closed`), `sent_at`, `status_updated_at`, `error` (stable code: `provider_rejected`, `provider_unavailable`, `send_failed`), `created_at`.

### Ava and reports
**ava_threads** — `id`, `workspace_id`, `member_id`, `scope` (`pipeline|workspace`), `pipeline_id`, `created_at`.
**ava_messages** — `id`, `workspace_id`, `thread_id`, `role` (`user|assistant`), `content jsonb` (paras, table, bullets, note, sources[]), `refused bool`, `model`, `created_at`.
**report_jobs** — `id`, `workspace_id`, `requested_by`, `kind` (`candidate_report|pipelines_report|resume_download|sample`; `sample` is the local-only demo job, FND-008), `params jsonb`, `status` (`queued|running|done|failed|cancelled`), `step`, `steps_total`, `file_path`, `error` (stable code, never a message), `created_at`, `finished_at`. Only the member in `requested_by` sees a job. Redis only queues the work; this row is the state people see (ADR-009).

### Billing
**subscriptions** — `workspace_id` PK, `stripe_subscription_id`, `plan` (`starter|growth|scale`), `status` (Stripe status), `current_period_start`, `current_period_end`, `pending_plan`, `cancel_at_period_end`, `default_payment_method_brand`, `default_payment_method_last4`, `default_payment_method_exp`.

**credit_batches** — `id`, `workspace_id`, `kind` (`trial|plan|extra`), `amount`, `remaining`, `added_at`, `expires_at`, `stripe_invoice_id`, `note`. Check `remaining between 0 and amount`; at most one `trial` batch per workspace (partial unique index).

**credit_ledger** (append-only) — `id`, `workspace_id`, `kind` (`grant_trial|grant_plan|purchase|consume|reserve|release|top_up|expire|adjust`), `amount` (signed, balance change; 0 for reserve moves), `reserve_change` (signed), `pipeline_id`, `application_id`, `batch_id`, `balance_after` (unexpired balance after the change), `actor_id` (no FK), `created_at`. Composite FKs to `pipelines` and `credit_batches`, and to `applications` (APPLY-003), which is `deferrable initially deferred`: a submission uses the credit first (locking the workspace and pipeline rows) and inserts the application later in the same transaction. The ledger's `amount` always sums to the batches' `remaining`.

**stripe_invoices** (cache) — `id` (Stripe ID), `workspace_id`, `number`, `kind` (`plan|credits`), `description`, `amount_cents`, `currency`, `status` (`paid|open|failed|void`), `hosted_url`, `pdf_url`, `created_at`.

**billing_details** — `workspace_id` PK, `company_legal_name`, `billing_email`, `address jsonb`, `tax_id` (synced to Stripe customer).

### Compliance and ops
**ai_decisions** (append-only, SCREEN-002) — `id`, `workspace_id`, `application_id` (no FK, so the log outlives the application), `type` (`resume_screen|interview_score|integrity_flag`), `outcome` (`pass|fail` for screens and interview scores; the flag type for `integrity_flag`), `score`, `threshold`, `model`, `prompt_version`, `input_ref` (e.g. `resume_texts:<application_id>@<redaction version>`), `output jsonb` (numbers and flags only, never résumé or transcript text), `created_at`.
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
- `transcript_segments` GIN on `to_tsvector('english', text)`; `(interview_id, start_ms)`.
- `interviews (completed_at)` where the recording is ready and the transcript is `none`/`processing` (requeue).

## 4. Analytics
Dashboards read from SQL views (`v_pipeline_funnel`, `v_source_stats`, `v_dropoff_reasons`, `v_time_to_screen`). `v_dropoff_reasons` (INTV-007, security invoker) has one row per live, unfinished interview with a drop reason: `workspace_id`, `pipeline_id`, `department_id`, `application_id`, `interview_id`, `drop_reason`, `status`, `dropped_at` (the expiry for `link_expired`, else when the last attempt ended); DASH-003 and PIPE-007 count it. The others (DASH-003, migration `20261010150000_analytics_views.sql`, security invoker, no access for `anon`/`authenticated`):
- `v_pipeline_funnel`: one row per application with `workspace_id`, `pipeline_id`, `department_id`, `application_id`, `candidate_id`, `source`, `applied_at`, `stage`, `stage_changed_at`, `has_open_flags`, `resume_passed`, `invited` (any interview issued), `interview_completed_at` (first finished interview), and the latest assessment's `interview_score`, `interview_passed`, `assessed_at`.
- `v_source_stats`: `v_pipeline_funnel` grouped by workspace, pipeline, department and source: `applicants`, `screened`, `resume_passed`, `interviewed`, `interview_passed`.
- `v_time_to_screen`: assessed applications with `seconds_to_interview` (applied → interview finished) and `seconds_to_assessment` (applied → assessed).

`app/repositories/analytics.py` reads them, always filtered by workspace and the caller's departments. Measured on the seed (1,081 applications), every dashboard endpoint answers under 400 ms at p95. If they get slow, convert to materialised views refreshed by cron — not in MVP unless measured.

## 5. Seed data
`apps/api/scripts/seed.py` (`make db-seed`, run by `make db-reset` and `make setup`) creates a demo workspace ("Acme Talent") with the departments, members, pipelines and sample candidates shown in the design, so every screen can be built against realistic data locally. It writes synthetic `.test` users straight into `auth.users`, so it connects as the database owner, and it moves credits only through `app/services/credits.py` so the ledger adds up. Each task that adds a table the screens show extends it (pipeline titles in PIPE-001, candidates and assessments later). `supabase/seed.sql` only sets the local API role password.

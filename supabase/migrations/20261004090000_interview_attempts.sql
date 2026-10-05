-- INTV-004 Realtime session service: one row per connection to the live AI interviewer. A
-- reconnect or a resume is a new attempt; the interview's talk_seconds is the sum of its
-- attempts' and is capped at 30 minutes (ADR-012). Design: docs/architecture/DATABASE.md,
-- docs/architecture/MEDIA.md §2 and docs/product/WORKFLOW.md §4. Written only by
-- apps/api/app/services/interview_sessions.py and the sideband job.

create table public.interview_attempts (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id),
  interview_id uuid not null,
  -- The OpenAI Realtime call id; set when the call is created.
  realtime_session_id text,
  started_at timestamptz not null default now(),
  -- First heartbeat saying the browser's connection is up; null = it never connected.
  connected_at timestamptz,
  -- Last heartbeat; the watchdog ends attempts that stop sending them.
  last_seen_at timestamptz,
  ended_at timestamptz,
  end_reason text check (
    end_reason in ('candidate_ended', 'wrap_up', 'time_cap', 'disconnect', 'error')
  ),
  -- What was left of the 30-minute cap when the attempt started: it ends at
  -- started_at + seconds_allowed whatever the browser does.
  seconds_allowed integer not null check (seconds_allowed > 0),
  talk_seconds integer not null default 0 check (talk_seconds >= 0 and talk_seconds <= seconds_allowed),
  -- The plan topic this attempt started from, and the furthest one the interviewer reached.
  resume_from integer not null default 0 check (resume_from >= 0),
  topic_index integer check (topic_index >= 0),
  wrap_up_sent_at timestamptz,
  check ((ended_at is null) = (end_reason is null)),
  -- Deleted with its interview (candidate deletion, PRIVACY.md).
  constraint interview_attempts_interview_fkey foreign key (workspace_id, interview_id)
    references public.interviews (workspace_id, id) on delete cascade
);

create index interview_attempts_interview_id_started_at_idx
  on public.interview_attempts (interview_id, started_at);
-- For the watchdog: attempts still open.
create index interview_attempts_open_idx
  on public.interview_attempts (started_at) where ended_at is null;

-- Lockdown: RLS on with no policies; no privileges for the public keys.
alter table public.interview_attempts enable row level security;

revoke all on public.interview_attempts from anon, authenticated;

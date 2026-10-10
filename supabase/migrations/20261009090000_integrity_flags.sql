-- ASMT-002 Integrity checks: flags for possible impersonation, at exact moments, for a person to
-- review (they never reject anyone on their own), and where an interview's checks are. Design:
-- docs/decisions/ADR-016, docs/architecture/MEDIA.md §5, docs/architecture/AI_PIPELINE.md §5 and
-- docs/compliance/FRAUD_INTEGRITY.md. Only apps/api/app/services/integrity.py creates flags;
-- resolving them comes with ASMT-003. No face embedding or frame is ever stored. Expand-only.

create table public.integrity_flags (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id),
  interview_id uuid not null,
  application_id uuid not null,
  type text not null
    check (type in ('different_face', 'no_face', 'second_voice', 'read_aloud', 'unusual_timing')),
  -- On the recording's clock.
  start_ms integer not null check (start_ms >= 0),
  end_ms integer not null,
  -- What the flag was raised on: numbers (seconds, similarity, delays against the session's
  -- baseline) and, for read_aloud, the model's one-sentence rationale. Never an embedding.
  detail jsonb not null default '{}'::jsonb,
  confidence numeric(3, 2) not null check (confidence between 0 and 1),
  status text not null default 'open'
    check (status in ('open', 'no_concern', 'concern_confirmed')),
  resolved_by uuid references public.profiles (id),
  resolved_at timestamptz,
  resolution_note text,
  created_at timestamptz not null default now(),
  constraint integrity_flags_times_check check (end_ms >= start_ms),
  constraint integrity_flags_resolved_check check (
    (status = 'open') = (resolved_at is null)
  ),
  -- Deleted with its application (candidate deletion, PRIVACY.md).
  constraint integrity_flags_application_fkey foreign key (workspace_id, application_id)
    references public.applications (workspace_id, id) on delete cascade,
  constraint integrity_flags_interview_fkey foreign key (workspace_id, interview_id)
    references public.interviews (workspace_id, id) on delete cascade
);

create index integrity_flags_interview_id_start_ms_idx
  on public.integrity_flags (interview_id, start_ms);
-- The Flagged filter (WORKFLOW.md §4): applications with at least one open flag.
create index integrity_flags_open_idx
  on public.integrity_flags (workspace_id, application_id)
  where status = 'open';

-- none: not checked yet; ready: the checks ran (flags, if any, exist); off: the pipeline's
-- "Flag possible impersonation" was off, so nothing ran; failed: the job gave up (nothing is
-- flagged, nothing waits on it).
alter table public.interviews
  add column integrity_status text not null default 'none'
    check (integrity_status in ('none', 'ready', 'off', 'failed')),
  -- Which checks ran, for the profile ("Face check not run"): {"face": ran | no_consent |
  -- voice_only | no_video, "second_voice": ran, "timing": ran | too_short, "read_aloud": ran |
  -- too_short | failed}.
  add column integrity_checks jsonb,
  add column integrity_checked_at timestamptz;

-- For requeue_stuck_work: transcribed interviews still waiting for their checks.
create index interviews_integrity_pending_idx
  on public.interviews (transcribed_at)
  where transcript_status = 'ready' and integrity_status = 'none';

-- Lockdown: RLS on with no policies; no privileges for the public keys.
alter table public.integrity_flags enable row level security;

revoke all on public.integrity_flags from anon, authenticated;

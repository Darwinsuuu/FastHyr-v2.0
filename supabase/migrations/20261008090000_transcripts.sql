-- INTV-008 Authoritative transcription: the timeline the server keeps of a live call, where each
-- attempt sits in the final recording, and the transcript the transcribe_interview job makes from
-- `audio.m4a`. Design: docs/architecture/DATABASE.md and docs/architecture/MEDIA.md §4. Written
-- only by apps/api (app/interview/sideband.py, services/recordings.py, services/transcripts.py).
-- Expand-only.

-- What the sideband saw during an attempt, on the server clock: the interviewer speaking (its own
-- response transcript, used to tell its voice apart in the recording) and topic changes. Nothing
-- the candidate says is stored here.
create table public.interview_events (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id),
  interview_id uuid not null,
  attempt_id uuid not null references public.interview_attempts (id) on delete cascade,
  kind text not null check (kind in ('ai_speech', 'topic')),
  -- ai_speech: the interviewer's audio started; topic: set_topic was accepted.
  at timestamptz not null,
  -- ai_speech only: the audio stopped (null when the call ended first).
  ended_at timestamptz,
  -- ai_speech only: the response id, and what the interviewer said.
  ref text,
  text text,
  -- topic only: the 0-based plan topic.
  topic_index integer check (topic_index >= 0),
  created_at timestamptz not null default now(),
  constraint interview_events_kind_fields_check check (
    (kind = 'topic' and topic_index is not null)
    or (kind = 'ai_speech' and topic_index is null)
  ),
  constraint interview_events_interview_fkey foreign key (workspace_id, interview_id)
    references public.interviews (workspace_id, id) on delete cascade
);

create index interview_events_interview_id_at_idx on public.interview_events (interview_id, at);
create unique index interview_events_attempt_id_ref_key
  on public.interview_events (attempt_id, ref) where ref is not null;

-- Where the attempt sits in the final recording, in milliseconds; null = left out of it (its
-- chunks couldn't be read) or not finalised yet.
alter table public.interview_attempts
  add column recording_offset_ms integer check (recording_offset_ms >= 0),
  add column recording_ms integer check (recording_ms >= 0);

alter table public.interviews
  add column transcript_status text not null default 'none'
    check (transcript_status in ('none', 'processing', 'ready', 'failed')),
  add column transcribed_at timestamptz;

-- For requeue_stuck_work: ready recordings still waiting for their transcript.
create index interviews_transcript_pending_idx
  on public.interviews (completed_at)
  where recording_status = 'ready' and transcript_status in ('none', 'processing');

-- The authoritative transcript (FR-ASMT-01): speaker-separated, timestamped against the final
-- recording, with the plan topic each line belongs to. Replaced whole when the job runs again.
create table public.transcript_segments (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id),
  interview_id uuid not null,
  -- 0-based order in the recording.
  seq integer not null check (seq >= 0),
  start_ms integer not null check (start_ms >= 0),
  end_ms integer not null,
  speaker text not null check (speaker in ('interviewer', 'candidate', 'other')),
  text text not null,
  -- 0-based plan topic; null when the interview has no attempts to place it in.
  topic_index integer check (topic_index >= 0),
  constraint transcript_segments_times_check check (end_ms >= start_ms),
  constraint transcript_segments_interview_id_seq_key unique (interview_id, seq),
  -- Deleted with its interview (candidate deletion, PRIVACY.md).
  constraint transcript_segments_interview_fkey foreign key (workspace_id, interview_id)
    references public.interviews (workspace_id, id) on delete cascade
);

create index transcript_segments_interview_id_start_ms_idx
  on public.transcript_segments (interview_id, start_ms);
-- Transcript search (ASMT-006, Ava's search_transcripts).
create index transcript_segments_text_search_idx
  on public.transcript_segments using gin (to_tsvector('english', text));

-- Lockdown: RLS on with no policies; no privileges for the public keys.
alter table public.interview_events enable row level security;
alter table public.transcript_segments enable row level security;

revoke all on public.interview_events from anon, authenticated;
revoke all on public.transcript_segments from anon, authenticated;

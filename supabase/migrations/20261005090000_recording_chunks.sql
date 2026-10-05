-- INTV-006 Recording capture and finalisation: the chunks a browser uploads while it records an
-- interview, and what each attempt's recording is. The finalize_recording job joins the chunks
-- into the interview's recording and deletes them. Design: docs/architecture/DATABASE.md,
-- docs/architecture/MEDIA.md §3 and docs/architecture/STORAGE.md. Written only by
-- apps/api/app/services/recordings.py. Expand-only.

-- Each attempt records one stream (MediaRecorder): WebM, or MP4 from Safari.
alter table public.interview_attempts
  add column recording_type text check (recording_type in ('webm', 'mp4')),
  -- The browser registered the attempt's last chunk: nothing more is coming for it.
  add column recording_stopped_at timestamptz;

create table public.recording_chunks (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id),
  interview_id uuid not null,
  attempt_id uuid not null references public.interview_attempts (id) on delete cascade,
  -- 0-based order within the attempt; the chunks join byte for byte in this order.
  seq integer not null check (seq >= 0),
  -- In the recordings bucket: {workspace_id}/{interview_id}/chunks/{attempt_id}/{seq}.{type}
  path text not null,
  bytes bigint not null check (bytes >= 0),
  uploaded_at timestamptz not null default now(),
  constraint recording_chunks_attempt_id_seq_key unique (attempt_id, seq),
  -- Deleted with its interview (candidate deletion, PRIVACY.md).
  constraint recording_chunks_interview_fkey foreign key (workspace_id, interview_id)
    references public.interviews (workspace_id, id) on delete cascade
);

create index recording_chunks_interview_id_idx on public.recording_chunks (interview_id);

-- For the finalize_recordings cron: completed interviews whose recording isn't done yet.
create index interviews_recording_pending_idx
  on public.interviews (completed_at)
  where status = 'completed' and recording_status in ('none', 'uploading', 'finalizing');

-- Lockdown: RLS on with no policies; no privileges for the public keys.
alter table public.recording_chunks enable row level security;

revoke all on public.recording_chunks from anon, authenticated;

-- Safari records MP4 (FND-011 allowed only WebM video).
update storage.buckets
set allowed_mime_types = array['video/webm', 'video/mp4', 'audio/webm', 'audio/mp4', 'image/jpeg']
where id = 'recordings';

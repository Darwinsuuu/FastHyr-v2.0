-- SCREEN-003 Post-screen actions: the interview a passed résumé is invited to, and the
-- "Request a human review" link of an automated rejection (ADR-015). Design:
-- docs/architecture/DATABASE.md and docs/product/WORKFLOW.md §3-4. apps/api/app/services/
-- post_screen.py creates both; INTV-002 and later interview tasks fill the interview's other
-- columns, and ASMT-008 turns a review link into a human_review_requests row.

create table public.interviews (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id),
  application_id uuid not null,
  -- SHA-256 of the link token; the token itself is only in the invitation email.
  token_hash text not null unique,
  format text not null check (format in ('video_voice', 'voice_only')),
  status text not null default 'not_started' check (
    status in ('not_started', 'in_progress', 'abandoned', 'completed', 'expired')
  ),
  drop_reason text check (drop_reason in ('link_expired', 'left_unfinished', 'technical_issue')),
  invited_at timestamptz not null default now(),
  expires_at timestamptz not null,
  reminder_sent_at timestamptz,
  started_at timestamptz,
  completed_at timestamptz,
  talk_seconds integer check (talk_seconds >= 0),
  consent_version text,
  consent_at timestamptz,
  -- The biometric notice id when given (COMP-002); null = not given.
  biometric_consent_version text,
  recording_path text,
  recording_status text not null default 'none' check (
    recording_status in ('none', 'uploading', 'finalizing', 'ready', 'failed')
  ),
  duration_seconds integer check (duration_seconds >= 0),
  feedback_rating integer check (feedback_rating between 1 and 5),
  feedback_comment text,
  -- The interview a re-invite replaced this one with (INTV-007).
  superseded_by uuid references public.interviews (id),
  check (expires_at > invited_at),
  constraint interviews_workspace_id_id_key unique (workspace_id, id),
  -- Deleted with its application (candidate deletion, PRIVACY.md).
  constraint interviews_application_fkey foreign key (workspace_id, application_id)
    references public.applications (workspace_id, id) on delete cascade
);

-- One live interview per application: a re-invite supersedes the old one first.
create unique index interviews_application_id_live_key
  on public.interviews (application_id) where superseded_by is null;
-- For the expiry and reminder crons (INTV-007).
create index interviews_status_expires_at_idx on public.interviews (status, expires_at);

create table public.review_links (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id),
  application_id uuid not null,
  -- Which automated decision the candidate may ask a person to review.
  decision_type text not null check (decision_type in ('resume', 'interview')),
  -- SHA-256 of the link token; the token itself is only in the rejection email.
  token_hash text not null unique,
  -- 30 days after the rejection email goes out (ASMT-008).
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  constraint review_links_application_id_decision_type_key unique (application_id, decision_type),
  constraint review_links_application_fkey foreign key (workspace_id, application_id)
    references public.applications (workspace_id, id) on delete cascade
);

-- Lockdown: RLS on with no policies; no privileges for the public keys.
alter table public.interviews enable row level security;
alter table public.review_links enable row level security;

revoke all on public.interviews, public.review_links from anon, authenticated;

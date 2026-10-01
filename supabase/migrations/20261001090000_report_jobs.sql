-- FND-008 Background jobs: report_jobs holds the progress of long jobs a user waits on (PDF
-- reports, résumé downloads), polled through GET /v1/jobs/{id}. Redis only queues the work;
-- the state people see lives here (ADR-009). Design: docs/architecture/DATABASE.md.

create table public.report_jobs (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id),
  requested_by uuid not null references public.profiles (id),
  -- `sample` is the local-only demo job of the job framework (FND-008).
  kind text not null check (
    kind in ('candidate_report', 'pipelines_report', 'resume_download', 'sample')
  ),
  params jsonb not null default '{}'::jsonb,
  status text not null default 'queued' check (
    status in ('queued', 'running', 'done', 'failed', 'cancelled')
  ),
  step integer not null default 0,
  steps_total integer not null default 1,
  file_path text,
  -- A stable error code, never a message that could carry personal data.
  error text,
  created_at timestamptz not null default now(),
  finished_at timestamptz,
  constraint report_jobs_step_check check (steps_total > 0 and step between 0 and steps_total)
);

create index report_jobs_workspace_id_requested_by_idx
  on public.report_jobs (workspace_id, requested_by);
-- The requeue_stuck_work sweeper looks for jobs that never left the queue.
create index report_jobs_queued_created_at_idx
  on public.report_jobs (created_at) where status = 'queued';

-- Lockdown: RLS on with no policies; no privileges for the public keys.
alter table public.report_jobs enable row level security;
revoke all on public.report_jobs from anon, authenticated;

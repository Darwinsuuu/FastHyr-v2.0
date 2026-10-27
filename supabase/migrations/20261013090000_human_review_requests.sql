-- ASMT-008 Human review requests (ADR-015, FR-COMP-03): a candidate opens the "Request a human
-- review" link of a rejection email (`review_links`, SCREEN-003) and asks a person to look at
-- the decision again; the team upholds it or overrides it. Only
-- apps/api/app/services/review_requests.py writes these rows. Expand-only.

create table public.human_review_requests (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id),
  application_id uuid not null,
  -- The decision the candidate asked about, copied from the link.
  decision_type text not null check (decision_type in ('resume', 'interview')),
  -- The link the request came through.
  review_link_id uuid not null,
  -- "Anything you'd like them to know?" (S-03), optional; only the team sees it.
  candidate_message text check (char_length(candidate_message) <= 1000),
  status text not null default 'open' check (status in ('open', 'upheld', 'overridden')),
  -- Workspace member ID (as advanced_by / rejected_by).
  resolved_by uuid,
  resolved_at timestamptz,
  -- Required to resolve ("Only your team sees this").
  resolution_note text check (char_length(resolution_note) <= 1000),
  created_at timestamptz not null default now(),
  constraint human_review_requests_resolved_check check (
    (status = 'open') = (resolved_at is null)
  ),
  -- Deleted with its application (candidate deletion, PRIVACY.md).
  constraint human_review_requests_application_fkey foreign key (workspace_id, application_id)
    references public.applications (workspace_id, id) on delete cascade,
  constraint human_review_requests_review_link_id_fkey foreign key (review_link_id)
    references public.review_links (id) on delete cascade,
  constraint human_review_requests_resolved_by_fkey foreign key (workspace_id, resolved_by)
    references public.workspace_members (workspace_id, id)
);

-- One open request per application; the "Review requested" overlay follows it.
create unique index human_review_requests_open_key
  on public.human_review_requests (application_id)
  where status = 'open';
create index human_review_requests_workspace_id_status_idx
  on public.human_review_requests (workspace_id, status, created_at);

-- When the link was used. A TA rejection that gives the link a new token (ASMT-007) clears it,
-- so the new decision can be reviewed too.
alter table public.review_links add column requested_at timestamptz;

-- Lockdown: RLS on with no policies; no privileges for the public keys.
alter table public.human_review_requests enable row level security;

revoke all on public.human_review_requests from anon, authenticated;

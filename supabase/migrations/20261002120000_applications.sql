-- APPLY-003 Application submission and credit use: candidates (one row per person per
-- workspace) and their applications, one per candidate per pipeline. Design:
-- docs/architecture/DATABASE.md (Candidates and applications) and docs/product/WORKFLOW.md §3.
-- Only apps/api/app/services/applications.py writes these rows.

-- ---------------------------------------------------------------------------
-- Candidates: the same person applying to two workspaces is two rows (MULTI_TENANCY.md)
-- ---------------------------------------------------------------------------
create table public.candidates (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id),
  -- The Google or Microsoft account they applied with (ADR-014). No FK: deleting the auth user
  -- must not touch the employer's records; candidate deletion (COMP) removes the row itself.
  auth_user_id uuid not null,
  email text not null,
  full_name text not null,
  -- Dialling code such as +63, and the number without it.
  phone_country_code text not null,
  phone text not null,
  city text,
  -- LinkedIn or portfolio.
  profile_url text,
  first_applied_at timestamptz not null default now(),
  last_activity_at timestamptz not null default now(),
  deleted_at timestamptz,
  constraint candidates_workspace_id_id_key unique (workspace_id, id),
  constraint candidates_workspace_id_auth_user_id_key unique (workspace_id, auth_user_id),
  constraint candidates_phone_country_code_check check (phone_country_code ~ '^\+[0-9]{1,4}$'),
  constraint candidates_phone_check check (phone ~ '^[0-9]{4,15}$')
);

-- ---------------------------------------------------------------------------
-- Applications
-- ---------------------------------------------------------------------------
create table public.applications (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id),
  pipeline_id uuid not null,
  candidate_id uuid not null,
  -- From the apply link's ?source= tag; direct when there was none.
  source text not null default 'direct' check (
    source in (
      'linkedin', 'jobstreet', 'indeed', 'kalibrr', 'glassdoor', 'facebook', 'careers', 'other',
      'direct'
    )
  ),
  resume_path text not null,
  resume_filename text not null,
  resume_pages integer not null check (resume_pages > 0),
  resume_bytes integer not null check (resume_bytes > 0),
  -- The notice id the candidate agreed to (COMP-002), e.g. apply@v1, and when. The IP is kept
  -- only as a keyed hash (FR-COMP-01).
  consent_version text not null,
  consent_at timestamptz not null,
  consent_ip_hash text,
  stage text not null default 'processing_resume' check (
    stage in (
      'processing_resume', 'resume_not_match', 'invited', 'interview_in_progress', 'scoring',
      'ready_for_review', 'did_not_pass', 'advanced', 'rejected'
    )
  ),
  stage_changed_at timestamptz not null default now(),
  resume_status text not null default 'pending' check (
    resume_status in ('pending', 'done', 'unreadable', 'error')
  ),
  fit text check (fit in ('strong', 'good')),
  overall_score integer check (overall_score between 0 and 100),
  has_open_flags boolean not null default false,
  review_requested boolean not null default false,
  rejected_reason text,
  rejected_by uuid,
  rejected_at timestamptz,
  advanced_note text,
  advanced_by uuid,
  advanced_at timestamptz,
  -- The consume entry for this application's credit (ADR-010).
  credit_ledger_id uuid not null references public.credit_ledger (id),
  applied_at timestamptz not null default now(),
  constraint applications_workspace_id_id_key unique (workspace_id, id),
  -- One application per candidate per pipeline (FR-APPLY-05).
  constraint applications_pipeline_id_candidate_id_key unique (pipeline_id, candidate_id),
  constraint applications_pipeline_fkey foreign key (workspace_id, pipeline_id)
    references public.pipelines (workspace_id, id),
  constraint applications_candidate_fkey foreign key (workspace_id, candidate_id)
    references public.candidates (workspace_id, id),
  constraint applications_rejected_by_fkey foreign key (workspace_id, rejected_by)
    references public.workspace_members (workspace_id, id),
  constraint applications_advanced_by_fkey foreign key (workspace_id, advanced_by)
    references public.workspace_members (workspace_id, id)
);

create index applications_workspace_id_pipeline_id_stage_idx
  on public.applications (workspace_id, pipeline_id, stage);
create index applications_workspace_id_candidate_id_idx
  on public.applications (workspace_id, candidate_id);
create index applications_pipeline_id_applied_at_idx
  on public.applications (pipeline_id, applied_at);

-- The credit ledger's application link (BILL-002 left it as a plain uuid). Deferred to commit:
-- a submission uses the credit first, which locks the workspace and pipeline rows before
-- anything else, then inserts the application in the same transaction.
alter table public.credit_ledger
  add constraint credit_ledger_application_fkey foreign key (workspace_id, application_id)
    references public.applications (workspace_id, id) deferrable initially deferred;

-- Lockdown: RLS on with no policies; no privileges for the public keys.
alter table public.candidates enable row level security;
alter table public.applications enable row level security;
revoke all on public.candidates, public.applications from anon, authenticated;

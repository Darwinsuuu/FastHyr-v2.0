-- SCREEN-002 Résumé assessment and decision: the résumé fit score with its evidence, and the
-- append-only log of every AI decision (ADR-015). Design: docs/architecture/AI_PIPELINE.md §1
-- steps 3–6, docs/decisions/ADR-013 and docs/architecture/DATABASE.md. Only
-- apps/api/app/services/screening.py writes these rows.

-- ---------------------------------------------------------------------------
-- Résumé assessments: one per screened application
-- ---------------------------------------------------------------------------
create table public.resume_assessments (
  application_id uuid primary key,
  workspace_id uuid not null references public.workspaces (id),
  -- Fit score 0–100, computed in code from the model's parts (ADR-013).
  score integer not null check (score between 0 and 100),
  -- {"must_haves": {"score", "weight", "points", "detail"}, "nice_to_haves": …, "experience": …,
  -- "skill_depth": …}; a part with no criteria is left out and its weight redistributed.
  breakdown jsonb not null,
  -- [{criterion, met, evidence_quote, strength 0–3, waived, note}] in the pipeline's order.
  must_have_results jsonb not null default '[]'::jsonb,
  -- [{criterion, found, where, evidence_quote}] in the pipeline's order.
  nice_to_have_results jsonb not null default '[]'::jsonb,
  -- [{value, statement}]
  impact jsonb not null default '[]'::jsonb,
  -- [{requirement, type, found, strength 1–3}]: what the interview should check.
  claims jsonb not null default '[]'::jsonb,
  -- [{employer, title, start_year, end_year, current, relevant}]
  experience_timeline jsonb not null default '[]'::jsonb,
  -- {total_years, companies, average_years_per_role, title_promotions}
  career_snapshot jsonb not null default '{}'::jsonb,
  -- The pipeline's résumé pass bar when screened, and the decision:
  -- passed = score >= pass_bar and every must-have met.
  pass_bar integer not null check (pass_bar between 0 and 100),
  passed boolean not null,
  model text not null,
  prompt_version text not null,
  screened_at timestamptz not null default now(),
  -- From applying to the decision (FR-SCREEN-06).
  duration_ms integer not null check (duration_ms >= 0),
  -- Deleted with its application (candidate deletion, PRIVACY.md).
  constraint resume_assessments_application_fkey foreign key (workspace_id, application_id)
    references public.applications (workspace_id, id) on delete cascade
);

-- ---------------------------------------------------------------------------
-- AI decisions (append-only): every automated outcome, for audit and human review (ADR-015)
-- ---------------------------------------------------------------------------
create table public.ai_decisions (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id),
  -- No FK: the log must never change when an application is deleted. It holds numbers and
  -- references only, never résumé or transcript text.
  application_id uuid not null,
  type text not null check (type in ('resume_screen', 'interview_score', 'integrity_flag')),
  -- resume_screen: pass | fail.
  outcome text not null,
  score integer,
  threshold integer,
  model text not null,
  prompt_version text not null,
  -- What the decision was made from, e.g. resume_texts:<application_id>.
  input_ref text not null,
  output jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index ai_decisions_workspace_id_application_id_idx
  on public.ai_decisions (workspace_id, application_id);

create function public.reject_ai_decisions_change() returns trigger
language plpgsql
set search_path = ''
as $$
begin
  raise exception 'ai_decisions is append-only';
end;
$$;

create trigger ai_decisions_append_only
  before update or delete on public.ai_decisions
  for each row execute function public.reject_ai_decisions_change();

create trigger ai_decisions_no_truncate
  before truncate on public.ai_decisions
  for each statement execute function public.reject_ai_decisions_change();

revoke update, delete, truncate on public.ai_decisions from fasthyr_api;

-- ---------------------------------------------------------------------------
-- Lockdown: RLS on with no policies; no privileges for the public keys.
-- ---------------------------------------------------------------------------
alter table public.resume_assessments enable row level security;
alter table public.ai_decisions enable row level security;

revoke all on public.resume_assessments, public.ai_decisions from anon, authenticated;
revoke all on function public.reject_ai_decisions_change() from anon, authenticated, public;

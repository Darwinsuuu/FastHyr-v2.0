-- INTV-001 Interview plan generation: the personal plan the AI interviewer follows for one
-- application (topics in order, résumé-anchored question seeds, claims to verify). Design:
-- docs/architecture/AI_PIPELINE.md §2 and docs/architecture/DATABASE.md. Only
-- apps/api/app/services/interviews.py writes these rows.

create table public.interview_plans (
  application_id uuid primary key,
  workspace_id uuid not null references public.workspaces (id),
  -- [{kind, title, goal, skills[], seeds[{question, resume_quote}]}] in interview order:
  -- kind warm_up first, candidate_questions last, skills topics between. Résumé quotes are
  -- copied from the redacted résumé text ("" when a seed has none).
  topics jsonb not null,
  -- [{claim, resume_quote, skill}]: what the interviewer should check.
  claims_to_verify jsonb not null default '[]'::jsonb,
  -- ai: the model's plan passed every check; fallback: built in code from the pipeline's
  -- skills to probe after the model failed, so the candidate is never held up by it.
  source text not null check (source in ('ai', 'fallback')),
  -- Version of the live interviewer instructions the plan was used with (INTV-004).
  instructions_version text,
  model text not null,
  prompt_version text not null,
  created_at timestamptz not null default now(),
  -- Deleted with its application (candidate deletion, PRIVACY.md).
  constraint interview_plans_application_fkey foreign key (workspace_id, application_id)
    references public.applications (workspace_id, id) on delete cascade
);

-- Lockdown: RLS on with no policies; no privileges for the public keys.
alter table public.interview_plans enable row level security;

revoke all on public.interview_plans from anon, authenticated;

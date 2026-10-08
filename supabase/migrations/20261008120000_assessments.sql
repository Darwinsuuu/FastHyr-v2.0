-- ASMT-001 Interview scoring: the explainable assessment of each completed interview, and where
-- an interview's scoring is. Design: docs/architecture/AI_PIPELINE.md §4,
-- docs/decisions/ADR-011 and docs/architecture/DATABASE.md. Only
-- apps/api/app/services/scoring.py writes these rows. Expand-only.

create table public.assessments (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id),
  application_id uuid not null,
  -- One assessment per completed interview.
  interview_id uuid not null unique,
  -- Σ criterion score × weight, rounded half up (computed in code, FR-ASMT-02).
  overall_score integer not null check (overall_score between 0 and 100),
  -- {"technical"|"communication"|"culture": {score, weight, points, signals[{name, score}],
  -- evidence[{source: interview|resume, quote, start_ms (interview), source_label}], held_back}}
  criteria jsonb not null,
  -- [{index, title, start_ms, questions, follow_ups, score}] for the plan topics the interview
  -- reached, in order.
  topics jsonb not null default '[]'::jsonb,
  -- {text with [n] references, refs[{source, quote, start_ms (interview), source_label}]}
  summary jsonb not null,
  -- [{title, reason}]
  strengths jsonb not null default '[]'::jsonb,
  probes jsonb not null default '[]'::jsonb,
  -- [{requirement, type, found, strength, status, start_ms}]: the résumé claims, as the
  -- interview left them (confirmed | partly_confirmed | not_covered | probe_next_round).
  claims_checked jsonb not null default '[]'::jsonb,
  -- From the transcript's timings, never from the model: answers, avg_answer_ms,
  -- avg_response_delay_ms, questions, follow_ups, candidate_questions, candidate_talk_ms,
  -- interviewer_talk_ms, talk_time_pct.
  answer_stats jsonb not null,
  -- {weight_technical, weight_communication, weight_culture, pass_mark} when scored.
  rubric_snapshot jsonb not null,
  -- passed = overall_score >= pass_mark.
  passed boolean not null,
  -- ADR-011: strong_fit = passed, overall >= 80 and every résumé must-have met; good_fit =
  -- passed; null otherwise.
  fit text check (fit in ('strong_fit', 'good_fit')),
  model text not null,
  prompt_version text not null,
  created_at timestamptz not null default now(),
  constraint assessments_fit_passed_check check (fit is null or passed),
  -- Deleted with its application (candidate deletion, PRIVACY.md).
  constraint assessments_application_fkey foreign key (workspace_id, application_id)
    references public.applications (workspace_id, id) on delete cascade,
  constraint assessments_interview_fkey foreign key (workspace_id, interview_id)
    references public.interviews (workspace_id, id) on delete cascade
);

create index assessments_workspace_id_application_id_idx
  on public.assessments (workspace_id, application_id);

-- none: not scored yet; ready: the assessment exists; failed: the scoring job gave up (the
-- application stays in `scoring` for a person).
alter table public.interviews
  add column assessment_status text not null default 'none'
    check (assessment_status in ('none', 'ready', 'failed'));

-- For requeue_stuck_work: transcribed interviews still waiting for their assessment.
create index interviews_assessment_pending_idx
  on public.interviews (transcribed_at)
  where transcript_status = 'ready' and assessment_status = 'none';

-- Lockdown: RLS on with no policies; no privileges for the public keys.
alter table public.assessments enable row level security;

revoke all on public.assessments from anon, authenticated;

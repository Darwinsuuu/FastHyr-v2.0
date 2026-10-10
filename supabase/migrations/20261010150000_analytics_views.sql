-- DASH-003 Analytics: the views every dashboard reads (DATABASE.md §4). They are row level, one
-- row per application (or per pipeline and source), so each dashboard filters by date range,
-- department and Hiring-manager shortlist itself in app/repositories/analytics.py. Security
-- invoker: they see exactly what the caller's role sees. v_dropoff_reasons came with INTV-007.
-- Expand-only.

-- Where each application has got to. resume_passed is null until the résumé is screened;
-- invited is true once any interview link was sent (re-invites included); the interview columns
-- come from the finished interview and its assessment.
create view public.v_pipeline_funnel with (security_invoker = true) as
select
  a.workspace_id,
  a.pipeline_id,
  p.department_id,
  a.id as application_id,
  a.candidate_id,
  a.source,
  a.applied_at,
  a.stage,
  a.stage_changed_at,
  a.has_open_flags,
  ra.passed as resume_passed,
  i.invited_at is not null as invited,
  i.completed_at as interview_completed_at,
  s.overall_score as interview_score,
  s.passed as interview_passed,
  s.created_at as assessed_at
from public.applications a
join public.pipelines p
  on p.workspace_id = a.workspace_id and p.id = a.pipeline_id
left join public.resume_assessments ra
  on ra.workspace_id = a.workspace_id and ra.application_id = a.id
left join lateral (
  select min(iv.invited_at) as invited_at, max(iv.completed_at) as completed_at
  from public.interviews iv
  where iv.workspace_id = a.workspace_id and iv.application_id = a.id
) i on true
left join lateral (
  select x.overall_score, x.passed, x.created_at
  from public.assessments x
  where x.workspace_id = a.workspace_id and x.application_id = a.id
  order by x.created_at desc
  limit 1
) s on true;

-- Per pipeline and apply-link source: how many applied and how far they got.
create view public.v_source_stats with (security_invoker = true) as
select
  workspace_id,
  pipeline_id,
  department_id,
  source,
  count(*) as applicants,
  count(*) filter (where resume_passed is not null) as screened,
  count(*) filter (where resume_passed) as resume_passed,
  count(*) filter (where interview_completed_at is not null) as interviewed,
  count(*) filter (where interview_passed) as interview_passed
from public.v_pipeline_funnel
group by workspace_id, pipeline_id, department_id, source;

-- How long assessed applications took: applying → finished interview ("time to screen",
-- FR-DASH-02) and applying → assessment ("time to assessment", FR-PIPE-11).
create view public.v_time_to_screen with (security_invoker = true) as
select
  workspace_id,
  pipeline_id,
  department_id,
  application_id,
  applied_at,
  interview_completed_at,
  assessed_at,
  extract(epoch from interview_completed_at - applied_at)::bigint as seconds_to_interview,
  extract(epoch from assessed_at - applied_at)::bigint as seconds_to_assessment
from public.v_pipeline_funnel
where assessed_at is not null;

revoke all on public.v_pipeline_funnel, public.v_source_stats, public.v_time_to_screen
  from anon, authenticated;

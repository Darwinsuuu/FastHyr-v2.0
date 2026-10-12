-- PIPE-008 Candidates tab: the list columns on applications that only the seed filled in.
-- `fit` and `overall_score` now come with the interview assessment (services/scoring.py) and
-- `has_open_flags` with the first open integrity flag (services/integrity.py); ASMT-003 clears it
-- when every flag is resolved. This fills them in for rows written before. Data only.

update public.applications a
set overall_score = latest.overall_score,
    fit = case latest.fit when 'strong_fit' then 'strong' when 'good_fit' then 'good' end
from (
  select distinct on (application_id) application_id, overall_score, fit
  from public.assessments
  order by application_id, created_at desc
) latest
where latest.application_id = a.id
  and a.overall_score is null;

update public.applications a
set has_open_flags = true
where not a.has_open_flags
  and exists (
    select 1 from public.integrity_flags f
    where f.application_id = a.id and f.status = 'open'
  );

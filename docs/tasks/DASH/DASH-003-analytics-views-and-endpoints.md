# DASH-003: Analytics views and endpoints

| Field | Value |
|---|---|
| Epic | DASH — Dashboard |
| Milestone | M5 Review |
| Status | Done |
| Size | M |
| Depends on | [PIPE-001](../PIPE/PIPE-001-pipeline-model-and-state-machine.md), [APPLY-003](../APPLY/APPLY-003-application-submission-and-credit-use.md), [INTV-007](../INTV/INTV-007-interview-lifecycle-resume-expiry-reminders-re-inv.md), [ASMT-001](../ASMT/ASMT-001-interview-scoring.md) |
| Requirements | FR-DASH-02, FR-DASH-04, FR-PIPE-11, FR-CAND-03 |
| Gap areas | G8, G1 |
| Design | Frames Overview, PipelinesV2, PipelineView, CandidatePool |
| Docs to read | [`architecture/DATABASE.md §4`](../../architecture/DATABASE.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
One analytics layer computes funnels, time-to-screen, sources and drop-offs for every dashboard, scoped by role.

## Scope
**In:**
- SQL views (`v_pipeline_funnel`, `v_source_stats`, `v_dropoff_reasons`, `v_time_to_screen`)
- `services/analytics.py` + endpoints used by Overview, Pipelines flow, pipeline dashboard, candidates dashboard

**Out:**
- —

## Acceptance criteria
- [x] Numbers match hand-computed fixtures
- [x] Department scope applied
- [x] p95 < 400 ms on seed data
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Hiring managers get shortlist numbers only (ready for review, advanced, or flagged after the interview); sections they can't see are `null`, never zero.
- Department scope is applied in the repository: Admins see every department including No department; Recruiters and Hiring managers only theirs.
- Percent changes are `null` when nobody applied in the period before, so the page shows no change instead of +∞.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Auto-approved: the owner asked for no plan approvals, see the Log.)_

1. **Views** (one migration, all `security_invoker`, no grants to `anon`/`authenticated`), row level so every dashboard can filter by date, department and shortlist itself:
   - `v_pipeline_funnel`: one row per application with its pipeline, department, candidate, source, `applied_at`, stage, `has_open_flags`, `resume_passed` (null until screened), `invited` (an interview link was ever sent), `interview_completed_at`, `interview_score`, `interview_passed`, `assessed_at`.
   - `v_source_stats`: per pipeline and source: applicants, screened, résumé passed, interviewed, passed the interview.
   - `v_time_to_screen`: per assessed application: applied → finished interview and applied → assessment, in seconds.
   - `v_dropoff_reasons` exists (INTV-007).
2. **Repository** `app/repositories/analytics.py` (`AnalyticsRepository`): workspace-scoped, plus the caller's departments (Admins: all, including No department) and, for Hiring managers where SECURITY.md says "shortlist numbers only", only shortlisted applications (ready for review, advanced, or flagged after the interview).
3. **Service** `app/services/analytics.py` and endpoints:
   - `GET /v1/analytics/pipelines-flow?range=week|30d` (view pipelines): the Pipelines page band over open pipelines. Cohort of applications that applied in the range: applied (+ change against the period before), processing, invited, not a match, interviewed, in progress, not started, ready for review, flagged, didn't pass; median hours from applying to assessment for assessments made in the range.
   - `GET /v1/analytics/overview?range=week|30d` (view overview): KPIs (applicants + change, ready for review + flagged, live/paused/scheduled pipelines, median time from applying to a finished interview + change), funnel (applied, résumé matched, finished the interview, passed) with interview completion, top 5 waiting candidates by score, 5 open pipelines closing soonest, applicants per week (8 weeks, Monday weeks in the workspace time zone, applied and passed), sources (all time, pass rate = passed the interview), drop-off reasons (last 30 days), needs attention (ready for review with oldest wait, flagged, paused for credits, running low: under 30 days of credits at the last 14 days' pace, plan credits expiring within 7 days, invites expiring within 3 days for Admins) and credits (balance, reserved, free, plan credits used) for roles that see credit usage. Review requests come with ASMT-008 and the plan name and renewal with BILL-001; DASH-004 adds them. Hiring managers get only the shortlist numbers (ready for review, flagged, advanced, top candidates, pipelines); the other sections are null.
   - `GET /v1/pipelines/{id}/dashboard` (view pipelines, department scope, 404 outside it): KPIs (candidates + new this week, ready for you, median time to assessment, credits used of reserved, days remaining, closes at), funnel (applied, invited, interviewed, ready for review + flagged), new applicants per day (14 local days), interview score histogram (tens) with the pass mark, sources (applicants, résumé pass rate), didn't-finish reasons and how many "Re-invite all" would reach.
   - `GET /v1/candidates/dashboard` (candidate pool; Hiring managers shortlisted only): KPIs (candidates, new this month, applied more than once, interviewed across N pipelines, passed an interview, median time to assessment), new candidates per month (6 months), applications per candidate (1, 2, 3, 4+) with pass rates of returning and first-time candidates, where applications ended up (count per stage), best sources (people, pass rate). Most common skills stay with CAND-002.
   - "This week" is the last 7 days and "30 days" the last 30, each compared with the period before; local days, weeks and months use the workspace time zone.
4. **Web:** `FlowSummary` on `/pipelines` reads `pipelines-flow` (`lib/pipelines/flow.ts` builds the four stages and their notes), shows each stage's note and detail line and the median; zeros only while loading. Regenerate the API client.
5. **Seed:** every credit the Acme Talent pipelines used becomes a sample application (candidates from the design's names, some returning, sources, stages, résumé screens, interview links, assessments and a few open flags) through `credits.consume(application_id=…)`, so the dashboards and the p95 check have realistic data.
6. **Tests:** hand-computed fixtures for each endpoint, department and shortlist scope, tenancy (404 / 403 across workspaces), and a timing check on the seed data.
7. **Docs:** API.md, DATABASE.md §4, AGENTS.md status, BOARD.md (DASH-003 Done; PIPE-007, PIPE-010 and BILL-006 Ready; CAND-002 and DASH-004 still wait on other tasks).

## Log
- 2026-10-10: branch `feature/dash-003-analytics`. Plan written and treated as approved (the owner asked for no plan approvals).
- 2026-10-10: built as planned. Decisions:
  - The Pipelines band counts applications to open pipelines (live, paused, out of credits) that applied in the range, and where they are now; a closed pipeline drops out.
  - "Review the N waiting" from the PipelinesV2 frame is left out until a filtered review destination exists (PIPE-008).
  - The seed's live pipelines opened recently, so the 30-day change shows large percentages; the numbers are real for that data.
  - The seed now turns every credit the Acme Talent pipelines used into a sample application (1,081 applications, 981 people), and Account Executive (cancelled) used 0, so no consume is left without an application.
- 2026-10-10: acceptance. Hand-counted fixtures in `tests/integration/test_analytics.py` (week numbers, change, medians, sources, repeats, Recruiter and Hiring manager scope, other workspaces refused). p95 over 40 requests on the seed: overview week 269 ms, overview 30d 355 ms, pipelines-flow 65 ms, pipeline dashboard 38 ms, candidates dashboard 151 ms. Band checked at 360, 768, 1024 and 1440 px, light and dark.

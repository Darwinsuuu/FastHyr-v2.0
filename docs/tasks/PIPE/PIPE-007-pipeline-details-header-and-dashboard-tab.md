# PIPE-007: Pipeline details — header and Dashboard tab

| Field | Value |
|---|---|
| Epic | PIPE — Pipelines |
| Milestone | M5 Review |
| Status | Done |
| Size | M |
| Depends on | [DASH-003](../DASH/DASH-003-analytics-views-and-endpoints.md), [PIPE-004](../PIPE/PIPE-004-pipelines-list.md) |
| Requirements | FR-PIPE-11 |
| Gap areas | G1, G8 |
| Design | Frame PipelineView (Dashboard) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users see how one pipeline is performing and can re-invite people who didn't finish.

## Scope
**In:**
- Header (status, department, format, opened, owner, share)
- Tabs scaffold
- KPIs, funnel, daily chart, score histogram, sources, drop-offs
- Re-invite all with confirmation (INTV-007 API)

**Out:**
- —

## Acceptance criteria
- [x] Numbers match analytics fixtures (the page shows `GET /v1/pipelines/{id}/dashboard` as is; DASH-003's fixtures cover the numbers)
- [x] Re-invite creates new links and sends invitations
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Auto-approved: the owner asked for no plan approvals, see the Log.)_

1. **API:** `GET /v1/pipelines/{id}` returns `PipelineDetail`: the pipeline plus its department (`{id, name}` or null) and owner (`PipelineOwner`, as on the list), read in one query by `PipelineRepository.detail()` within the caller's departments. Nothing else changes: the Dashboard tab reads DASH-003's `GET /v1/pipelines/{id}/dashboard` and "Re-invite all" calls INTV-007's `POST /v1/pipelines/{id}/reinvite {scope: all_unfinished}`. Regenerate the API client.
2. **Web route:** `/pipelines/[id]` renders `PipelineDetailPage` (`components/pipelines/pipeline-detail-page.tsx`) under `RequireAccess view_pipelines`; the tab lives in `?tab=` (`dashboard` default, `candidates`, `ava`, `setup`) so links like "Review them" and the browser's back button work. A draft goes to its wizard (`/pipelines/{id}/edit`); a pipeline outside the member's departments shows not found.
3. **Header (frame PipelineView):** "All pipelines" back link, title, status pill, department (or No department), interview format, "Opened {date}" (scheduled: "Opens {date}"; never opened: nothing), owner avatar and name. "Share apply link" shows disabled until PIPE-006 builds the share modal (same rule PIPE-004 used for Copy apply link).
4. **Tabs scaffold:** Dashboard · Candidates (count) · Ask Ava · Setup with the kit `Tabs`; Candidates (PIPE-008), Ask Ava (AVA-002) and Setup (PIPE-009) show a short "coming with its own task" panel until built.
5. **Dashboard tab:** KPIs (Candidates + new this week, Ready for you + "Review them", Time to assessment median days, Credits used of reserved with a bar, Days remaining + closing date, or Closed/Cancelled {date} once ended), "Where candidates are" funnel (each a share of the step before), New applicants per day (14 local days), Interview scores histogram with the pass mark, Where applicants came from (applicants and résumé pass rate), Didn't finish the interview (reasons, share of invited) with "Re-invite all N" behind a confirm dialog; Recruiters outside `decide_candidates` (Hiring managers) don't see the button, and it is disabled when nobody can be re-invited or the pipeline is cancelled. After re-inviting, a toast says how many got a new link and the dashboard reloads. Pure helpers (funnel rates, histogram bins and pass-mark position, source labels, header facts) in `lib/pipelines/detail.ts`.
6. **Billing:** the owner moved billing last; Top up stays out of this page (BILL-006).
7. **Tests:** API: detail returns department and owner, department scope 404, other workspace 404. Web unit tests for `lib/pipelines/detail.ts`. Hand check at 360, 768, 1024 and 1440 px, light and dark, with the seed.
8. **Docs:** API.md, SCREENS.md if needed, AGENTS.md status, BOARD.md (PIPE-007 Done; PIPE-008 and PIPE-009 Ready when their other dependencies are done).

## Log
- 2026-10-11: branch `feature/pipe-007-pipeline-detail-dda5u1`. Plan written and treated as approved (the owner asked for no plan approvals). The owner moved billing tasks last, so no billing pieces here.
- 2026-10-11: built as planned. Decisions and findings:
  - "Share apply link" shows disabled until PIPE-006 builds the share window (same rule as Copy apply link in the Pipelines list). Candidates, Ask Ava and Setup tabs show an "on its way" panel until PIPE-008, AVA-002 and PIPE-009.
  - A draft opened at `/pipelines/{id}` goes to its wizard; Hiring managers don't see "Re-invite all" (no `decide_candidates`); it is disabled when nobody can be re-invited or the pipeline is cancelled.
  - The frame changes nothing on click; the task asks for a confirmation, so the button opens a confirm dialog, then a toast says how many got a new link.
  - Bug found while checking Re-invite all on the seed (12 candidates): from the sixth email on one connection, the dedupe insert in `repositories/emails.add_unless_duplicate()` failed with "no unique or exclusion constraint matching the ON CONFLICT specification", because the partial index predicate was a bound parameter and asyncpg's prepared statement had switched to a generic plan. The predicate is now literal SQL; `test_many_unique_emails_on_one_connection` fails without the fix.
- 2026-10-11: acceptance. Checked by hand on the seed as Dana (Admin), Maria (Recruiter) and Jomar (Hiring manager): live, scheduled and closed pipelines, Re-invite all on Senior Backend Engineer (12 new links, 12 invitations sent, 12 reminders scheduled), 360, 768, 1024 and 1440 px, light and dark.

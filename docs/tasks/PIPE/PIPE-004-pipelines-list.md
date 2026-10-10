# PIPE-004: Pipelines list

| Field | Value |
|---|---|
| Epic | PIPE — Pipelines |
| Milestone | M2 Pipelines |
| Status | Done |
| Size | M |
| Depends on | [PIPE-001](../PIPE/PIPE-001-pipeline-model-and-state-machine.md), [DASH-001](../DASH/DASH-001-app-shell.md) |
| Requirements | FR-PIPE-08 |
| Gap areas | G8 |
| Design | Frame PipelinesV2 |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users see all their pipelines, sorted so the ones that need them come first.

## Scope
**In:**
- Flow summary (week/30 days; real numbers after DASH-003, placeholder zeros before)
- Tabs, search, table, pagination
- Row menus per status (actions wired in PIPE-005)

**Out:**
- —

## Acceptance criteria
- [x] Counts per tab correct
- [x] Department scope applied
- [x] Days remaining / status labels as designed
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Conflict: WORKFLOW.md said drafts are not in the list, but then a draft saved with "Save as draft" had no way back into the wizard. Darwin chose a fifth Drafts tab after Closed (the frame has four tabs); drafts also show under All, with a Draft label and "Continue setup" (WORKFLOW.md §2 updated).
- "To review" counts applications in `ready_for_review` without open integrity flags: flagged ones wait under the Flagged filter (WORKFLOW.md §3, ASMT-003).
- The seed has no applications yet, so Acme Talent shows 0 candidates next to its used credits.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
1. **Database:** migration `20261010090000_pipeline_ended_at.sql` adds `pipelines.ended_at` (when it closed or was cancelled; `closes_at` is only the planned date), backfilled; `services/pipelines.py` sets it on close (the planned date when closed on schedule) and cancel; the seed sets it.
2. **API:** `GET /v1/pipelines?tab=&q=&page=&page_size=` (`view_pipelines`). `PipelineRepository.count_by_status()`, `to_review()` and `list_page()` (department scope through `_in_scope()`, archived hidden, title/department search with literal text, one grouped count of applications per pipeline, sort by an attention rank then the tie-breakers in API.md). `services/pipelines.list_pipelines()` maps tabs to statuses (`TAB_STATUSES`) and returns counts, `to_review` and the workspace time zone. Schemas `PipelineList`, `PipelineListItem`, `PipelineOwner`, `PipelineTabCounts`.
3. **Web:** `/pipelines` renders `PipelinesPage` (`components/pipelines/pipelines-page.tsx`): greeting with what's ready, flow summary on the kit `FlowBand` with zeros until DASH-003, tabs Live/Scheduled/Closed/Drafts/All with counts (kit `SegmentedControl` gains `count`), debounced search, the kit `Table` (cards on phones) and `Pagination` (5/10/25). Labels, credit tone and row menus are pure functions in `lib/pipelines/list.ts`. Row menus follow the frame per status and role; entries whose work belongs to PIPE-005 (lifecycle), PIPE-006 (copy link) and BILL-006 (top up) show disabled. `/pipelines/[id]` is a placeholder until PIPE-007 so row links don't 404. The Reports button waits for PIPE-010.
4. **Tests:** API integration tests for tabs/counts/archived, attention order and to-review counts, search and paging, department scope; web unit tests for labels, credit tone and menus; the new-pipeline e2e now finds the saved draft in the list.

## Log
- 2026-10-10: Branch `feature/pipe-004-pipelines-list` from `develop`. Plan auto-approved (owner's standing rule: no plan approvals). Picked PIPE-004 because ASMT-003 still waits on ASMT-004.
- Drafts: Darwin chose their own Drafts tab (see Notes).
- PR: #51.

# PIPE-008: Pipeline details — Candidates tab

| Field | Value |
|---|---|
| Epic | PIPE — Pipelines |
| Milestone | M5 Review |
| Status | Done |
| Size | M |
| Depends on | [PIPE-007](../PIPE/PIPE-007-pipeline-details-header-and-dashboard-tab.md), [APPLY-003](../APPLY/APPLY-003-application-submission-and-credit-use.md) |
| Requirements | FR-PIPE-12, FR-PIPE-13 |
| Gap areas | G5, G6, G7 |
| Design | Frame PipelineView (Candidates) + A-02, A-03 |
| Docs to read | [`design/SCREEN_SPECS.md A-02, A-03`](../../design/SCREEN_SPECS.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users filter a pipeline's candidates by stage and act on each one.

## Scope
**In:**
- Stage filters incl. Review requested, Advanced, Rejected
- Table with fit tooltip, source, applied time
- Row menu: profile, résumé, report, review flag, email, advance, reject (dialogs from ASMT-007)
- Polling while candidates are processing

**Out:**
- —

## Acceptance criteria
- [x] Filter counts correct
- [x] HM sees only shortlisted rows and no actions
- [x] Search by name/email
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

1. **API `GET /v1/pipelines/{id}/applications?stage=&q=&page=&page_size=`** (`VIEW_CANDIDATES`; Hiring managers get the shortlist: Ready for review, Flagged, Advanced). The pipeline must be in the caller's departments (else `404`). `stage` filters: `all`, `processing` (processing résumé), `not_a_match`, `invited`, `in_progress` (interview in progress or scoring), `ready` (ready for review, no open flags), `did_not_pass` (no open flags), `flagged` (open flags on a ready or did-not-pass application, WORKFLOW.md §3), `review_requested` (overlay), `advanced`, `rejected`. `q` matches the candidate's name or email (literal text). `page_size` 10/25/50. Returns `{items, total, page, page_size, counts, shortlist_only, pass_mark, timezone}`; `counts` has every filter, before the search. Each item: application id, candidate (id, name, email), stage, `flagged`, `review_requested`, `fit`, `overall_score`, must-haves met of total (résumé screen), strongest interview criterion, open flag types, source, `applied_at`. Sorted needing attention first: ready, flagged, in progress, scoring, invited, processing, advanced, didn't pass, not a match, rejected; then score (high first) and newest. Read by `PipelineCandidatesRepository` (`repositories/pipeline_candidates.py`), the page's details in a few extra queries.
2. **Overlay and fit columns kept up to date:** nothing wrote `applications.fit`, `overall_score` or `has_open_flags` outside the seed. `services/scoring.py` now sets `fit`/`overall_score` with the assessment, and `services/integrity.py` sets `has_open_flags` when it stores an open flag; a migration backfills both from `assessments` and `integrity_flags`.
3. **Web Candidates tab** (`components/pipelines/pipeline-candidates.tsx`, helpers in `lib/pipelines/candidates.ts`): stage filter chips with counts (`?stage=` in the URL, so "Review them" lands on Ready for review), search, the table (candidate avatar, name and email · stage pill with "Flagged" and "Review requested" badges · fit pill with the explanation tooltip, "—" before a passed interview · source · applied date and time in the workspace time zone), pagination 10/25/50, phone cards. Hiring managers see only All, Ready for review, Flagged and Advanced.
4. **Row menu (FR-PIPE-13):** View candidate profile (ASMT-004), Download résumé and Download candidate report if interviewed (ASMT-009), Review flag if flagged (ASMT-003), Email candidate (mailto, works now), Advance to next round (ready, or flagged with every flag resolved) and Reject candidate (ASMT-007). Items whose task isn't built yet show disabled with a note, the same rule PIPE-004 used. Hiring managers get only the profile and download items.
5. **Polling:** while anyone is processing a résumé, in an interview or being scored, the tab re-reads every 15 s.
6. **Tests:** API filters and counts, search, shortlist for Hiring managers, department scope and other-workspace 404 (tenancy), scoring/integrity setting the overlay columns. Web unit tests for `lib/pipelines/candidates.ts`. Hand check at 360, 768, 1024 and 1440 px, light and dark, with the seed as Dana, Maria and Jomar.
7. **Docs:** API.md, SCREENS.md, AGENTS.md status, BOARD.md (PIPE-008 Done; tasks it unblocks Ready).

## Log
- 2026-10-12: branch `feature/pipe-008-y6gxdh`. Plan written and treated as approved (the owner asked for no plan approvals). Billing goes last, so nothing here touches it.
- 2026-10-12: built as planned. Decisions and findings:
  - Nothing outside the seed wrote `applications.fit`, `overall_score` or `has_open_flags`, so real candidates would never show a fit or appear under Flagged. Scoring now writes the first two and the integrity checks set the overlay; migration `20261012090000_application_list_columns.sql` backfills them.
  - "In progress" holds interviews in progress and being scored (the frame has no Scoring filter; the row's pill still says Scoring), so the stage filters add up to All.
  - Flagged rows show a Flagged badge instead of Ready for review / Didn't pass (WORKFLOW.md §3); Review requested is an extra badge. A rejected candidate's fit badge is hidden, as in the frame.
  - The row menu shows every FR-PIPE-13 item the role and stage allow. View profile, the downloads, Review flag, Advance and Reject are disabled until ASMT-004, ASMT-009, ASMT-003 and ASMT-007 build them (the PIPE-004 rule); Email candidate opens the mail app. Candidate names aren't links until the profile exists. Hiring managers get the profile and downloads only.
  - Applied shows from `xl` and Source from `xl`: at `lg` with the sidebar the table didn't fit.
  - The seed's résumé screens now carry must-have results and its assessments criterion scores (from a separate random generator, so the sample applications are unchanged), so the fit explanation reads like real data.
- 2026-10-12: acceptance. Checked by hand on the seed (Senior Backend Engineer, 142 candidates) as Dana (Admin), Maria (Recruiter) and Jomar (Hiring manager: 15 shortlisted, four filters, no decisions in the menu), filters, search, the fit tooltip, the menu, Review requested (set by hand in the database), 360, 768, 1024 and 1440 px, light and dark.

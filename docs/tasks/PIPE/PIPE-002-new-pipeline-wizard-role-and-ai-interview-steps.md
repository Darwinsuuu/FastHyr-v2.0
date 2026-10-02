# PIPE-002: New pipeline wizard — Role and AI interview steps

| Field | Value |
|---|---|
| Epic | PIPE — Pipelines |
| Milestone | M2 Pipelines |
| Status | In review |
| Size | L |
| Depends on | [PIPE-001](../PIPE/PIPE-001-pipeline-model-and-state-machine.md), [WS-002](../WS/WS-002-departments.md), [FND-012](../FND/FND-012-ui-kit-design-system-components.md) |
| Requirements | FR-PIPE-01, FR-PIPE-02 |
| Gap areas | G2, G3, G4 |
| Design | Frame NewPipeline steps 1–2 + A-01 |
| Docs to read | [`design/SCREEN_SPECS.md A-01`](../../design/SCREEN_SPECS.md), [`decisions/ADR-013-resume-screening-rule.md`](../../decisions/ADR-013-resume-screening-rule.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users describe the role, screening criteria and interview style in the first two wizard steps.

## Scope
**In:**
- Wizard shell (vertical stepper, Save as draft, Cancel, Back/Continue with blocking hints)
- Step 1 fields incl. nice-to-haves and résumé pass bar
- Step 2 fields and toggles
- Draft autosave on step change

**Out:**
- Steps 3–5 (PIPE-003)

## Acceptance criteria
- [x] Min-3 rules for must-haves and skills enforced with the designed messages
- [x] Draft reload restores all fields
- [x] Department list comes from the workspace
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Fairness hint text under must-haves as designed

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Functional: min-3 must-haves/skills rule blocks Continue; draft save and reload keeps all fields

## Implementation plan
_(Auto-approved: the owner doesn't review plans.)_

**Routes.** `/pipelines/new` and `/pipelines/[id]/edit` in `app/ta/(app)/pipelines/`, both behind `<RequireAccess action="edit_pipelines">` and rendering one `PipelineWizard` (`components/pipelines/`). The PIPE-001 API already stores every field, so the wizard only calls `POST /v1/pipelines`, `GET` and `PATCH /v1/pipelines/{id}`.

**Form logic** in `lib/pipelines/wizard.ts` (unit tested): the form state for steps 1–2, defaults for a new pipeline, `formFromPipeline()` to restore a draft, `setupFromForm()` to build the request body (trimmed, empty text sent as null), `blockedHint()` for the min-3 rules, and `departmentOptions()`.

**Drafts.** Continue, Back, a click on a done step and "Save as draft" save the draft when anything changed. The first save creates it and swaps the URL to `/pipelines/{id}/edit` without a reload, so refreshing restores every field. A save that fails keeps the person on the step with an error toast. A pipeline that is no longer a draft or scheduled shows a "setup is locked" state (409 `pipeline_locked` does the same).

**Departments.** The picker lists the workspace's departments from `GET /v1/departments`. The API only lets Recruiters file pipelines under their own departments, so `Department` gains `assigned` (true for every department for Admins); the picker shows Admins "No department" plus every department, and Recruiters only theirs.

**Step 1 (Role):** title, department, employment type, work setup, location, job description, résumé must-haves (min 3, "Hidden from candidates", fairness note), nice-to-haves and the résumé pass bar (A-01, default 60), and "Also open to" cards with the note. **Step 2 (AI interview):** format cards, the adaptive-interview note, tone cards, seniority, skills to probe (min 3), link expiry and the reminder and impersonation toggles. Continue is blocked below 3 must-haves or skills with the designed hint; the counter turns red after a blocked try.

**Steps 3–5** show the stepper and a short "coming next" panel until PIPE-003 builds them.

**Responsive.** Phones and tablets get the compact "Step n of 5" header (the kit `Stepper` gains `expandAt="lg"`) and a sticky Back/Continue bar; the vertical stepper sits on the left from `lg`. Choice cards stack on phones.

**Tests.** Vitest for the form logic (min-3 rules, round trip of a saved draft); Playwright: min-3 blocks Continue, draft save and reload keeps all fields.

## Log
- 2026-10-02: Branch `feature/next-after-pipelines-l66ccm` from `develop`. Plan auto-approved (the owner doesn't review plans).
- Defaults for a new pipeline (not in the frame, which shows sample data): Full-time, On-site, Video + voice, Warm, Mid-level, link expiry 5 days, both toggles on, résumé pass bar 60.
- `GET /v1/departments` gained `assigned` per department so a Recruiter's picker lists only the departments the API accepts; Admins also get No department.
- Must-haves and skills use the kit's `ChipInput` (Enter, comma or leaving the field adds an item) instead of the frame's separate Add button.
- The vertical stepper shows from `xl`: at 1024 px the app sidebar leaves too little room beside it, so 1024 uses the compact header like tablets. `Stepper` gained `expandAt`.
- Steps 3 to 5 show a "This step is on its way" panel until PIPE-003. The Pipelines placeholder page gained a New pipeline button (PIPE-004 replaces the page).
- New kit component `ChoiceCards` (interview format, tone).

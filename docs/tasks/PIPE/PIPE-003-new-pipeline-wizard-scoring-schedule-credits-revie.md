# PIPE-003: New pipeline wizard — Scoring, Schedule & credits, Review, Publish

| Field | Value |
|---|---|
| Epic | PIPE — Pipelines |
| Milestone | M2 Pipelines |
| Status | In review |
| Size | L |
| Depends on | [PIPE-002](../PIPE/PIPE-002-new-pipeline-wizard-role-and-ai-interview-steps.md) |
| Requirements | FR-PIPE-03, FR-PIPE-04, FR-PIPE-05, FR-PIPE-06 |
| Gap areas | G4, G5 |
| Design | Frame NewPipeline steps 3–5, done state |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users set scoring, schedule and credits, review everything and publish with a clear lock warning.

## Scope
**In:**
- Rubric sliders with sum check, pass mark, message toggles
- Open now/scheduled, duration, close date, credit reserve stepper with free-credit check
- Review cards with Edit links
- Type-to-confirm publish/schedule dialog
- Done state with share tiles (PIPE-006 component)
- Edit setup for scheduled pipelines

**Out:**
- —

## Acceptance criteria
- [x] Can't continue unless weights = 100
- [x] Reserve > free credits shows the designed warning and blocks publish
- [x] Publishing live locks setup; scheduled stays editable until open
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Playwright: create and publish a pipeline

## Implementation plan
**API.** The PIPE-001 routes already store every field and publish (`POST /v1/pipelines/{id}/publish {confirm: "I understand"}` reserves the credits and fixes the slug). One new read: `GET /v1/credits/summary` → `{balance, reserved, free}` from `services/credits.summary()`, for anyone who can see credit usage (Admins, Recruiters), so the wizard can check the reserve against the free credits before publishing. BILL-006 can reuse it.

**Form logic** (`lib/pipelines/wizard.ts`, unit tested): the form grows the step 3–4 fields (weights, pass mark, message toggles, open mode, opening date, duration, reserve). New pipelines start at 50 / 30 / 20, pass mark 70, both messages on, open now, 90 days and a reserve of 100 or the free credits rounded down to 10s, whichever is smaller (min 10). `setupFromForm()` leaves the weights out while they don't add up to 100 (so "Save as draft" never fails on a half-moved slider), sends the opening date as local midnight, and for a scheduled pipeline leaves out `open_mode` and `credits_to_reserve`, which the API won't change after scheduling. `blockedHint()` blocks Continue on Scoring until the weights total 100; `publishBlock()` blocks Publish while anything the API would refuse is missing (title, description, location unless remote, 3 must-haves and skills, weights, a future opening date, a reserve within the free credits).

**Step 3, Scoring:** rubric sliders (0–100, step 5) with the "Adds up to 100%" pill, pass mark slider (40–95, step 5), Candidate messages toggles.
**Step 4, Schedule & credits:** Open now / Schedule a date cards, the date (tomorrow onwards), duration segments with "Closes on …", and the reserve `NumberStepper` (min 10, step 10) with the bar, the designed warning when it is more than the free credits, and the three explainers. For a scheduled pipeline the open mode and reserve are read only, with a note pointing to the Pipelines page.
**Step 5, Review:** the lock banner, four review cards with Edit links (missing required details shown as "Not set"), and Publish / Schedule pipeline, which opens the kit's `TypeToConfirmDialog` ("I understand"). For a scheduled pipeline the button is "Save changes" and goes back to Pipelines with a toast. `insufficient_free_credits` and `pipeline_incomplete` from the API show an error toast and keep the dialog open.
**Done state:** "{title} is live" / "{title} opens {date}", the editable-until note for scheduled pipelines, `ShareTiles` (new `components/pipelines/share-tiles.tsx`: 8 sources, copies `{site}/apply/{workspace-slug}/{pipeline-slug}?source={id}` and shows the board's hint; PIPE-006 wraps it in the share modal), Go to pipelines and Create another. `ShellWorkspace` gains `slug`.

**Responsive.** Same shell as steps 1–2: compact header and sticky footer below `xl`; rubric rows stack on phones; open-mode cards stack on phones; duration segments are full width; review rows stack term over value on phones; share tiles are 2 columns on phones, 4 from `sm`.

**Tests.** Vitest for the new form logic (weights rule, publish block, scheduled body); pytest for `GET /v1/credits/summary` (values, Hiring manager 403); Playwright: fill all five steps and publish, see the share tiles; the weights rule blocks Continue.

## Log
- 2026-10-02: Branch `feature/pipeline-wizard-publish-1b9vol` from `develop`.
- New read `GET /v1/credits/summary` (Admin, Recruiter) for the reserve check; there was no credits endpoint a Recruiter could call (`/billing/summary` is Admin only).
- Defaults for a new pipeline: weights 50 / 30 / 20, pass mark 70, both messages on, open now, 90 days, reserve 100 or the free credits rounded down to 10s (a new workspace's 20 trial credits give 20).
- The opening date is local midnight in the browser's time zone. Workspace time zones arrive with WS-001; switch to it then.
- The reserve over the free credits shows the designed warning on step 4 and blocks Publish on Review (the frame doesn't block Continue on step 4).
- Weights that don't add up to 100 are left out of draft saves, so "Save as draft" never fails mid-edit; the draft keeps its last valid weights.
- Editing a scheduled pipeline: open mode and reserve are read only (the API refuses changing them; Start now and top-up are PIPE-005 / BILL-006), Review's button is "Save changes", and the header says "Save changes" instead of "Save as draft".
- "Edit templates" link from the frame's Candidate messages card is left out until MSG-002 builds the page.
- Share tiles built here as `ShareTiles` for PIPE-006 to reuse; each tile shows its board's hint from the PipelinesV2 share modal after copying.
- "Create another" resets the wizard in place and moves the URL back to `/pipelines/new`.
- Kit changes: full-width `SegmentedControl` segments tighten on phones (4 durations fit at 360 px); rubric and pass-mark sliders got accessible names.

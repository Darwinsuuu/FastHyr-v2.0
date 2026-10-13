# ASMT-003: Flag review UI

| Field | Value |
|---|---|
| Epic | ASMT — Assessment & review |
| Milestone | M5 Review |
| Status | Done |
| Size | S |
| Depends on | [ASMT-002](../ASMT/ASMT-002-integrity-checks-worker.md), [ASMT-004](../ASMT/ASMT-004-candidate-profile-header-and-overview-tab.md) |
| Requirements | FR-ASMT-06 |
| Gap areas | G7 |
| Design | Frame CandidateProfile (integrity) + A-04 |
| Docs to read | [`design/SCREEN_SPECS.md A-04`](../../design/SCREEN_SPECS.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users review each flag with context and record their conclusion.

## Scope
**In:**
- Flag panel with jump-to moments and guidance
- Resolve (No concern / Concern confirmed + note)
- Flagged overlay cleared when all resolved

**Out:**
- —

## Acceptance criteria
- [x] Resolution audited
- [x] Advance enabled only after all flags resolved (the web gates Advance on `flagged`; ASMT-007's API must refuse it too, noted there)
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
No migration: `integrity_flags` already has `status`, `resolved_by`, `resolved_at` and `resolution_note` (ASMT-002).

1. **API `PATCH /v1/integrity-flags/{id}` `{status, note}`** (API.md), action `RESOLVE_REVIEWS` (Admins; Recruiters in their departments; Hiring managers 403). `services/integrity_reviews.resolve()`: the flag in the workspace, its application's pipeline in the caller's departments and the candidate not deleted, else 404. Locks the application row so two reviewers finishing the last two flags together can't leave the overlay on. `status` is `no_concern` or `concern_confirmed`; the note is up to 1,000 characters, optional for No concern and required for Concern confirmed (`422`). Sets `resolved_by`/`resolved_at`/`resolution_note`; a reviewed flag can be reviewed again (it never goes back to open). When the application has no open flags left, `has_open_flags` is cleared, so it leaves the Flagged filter for Ready for review or Didn't pass. One `audit_log` row per review (`integrity_flag.resolved`: application, type, from, to; never the note). Returns the flag and the application's `flagged`/`open_flags`.
2. **Profile** `GET /v1/applications/{id}`: each flag also carries `resolved_at`, `resolved_by` (name) and `note`; the web decides who may review from `resolve_reviews` in `lib/permissions.ts`.
3. **Web, A-04 on the Overview "Integrity checks" card**: each open flag gets its moments (jump-to buttons, Likely/Possible), the FRAUD_INTEGRITY.md §3 guidance, a "No concern" / "Concern confirmed" segmented control, a note and "Save review"; reviewed flags show the outcome, who and when, the note and "Change review". The card spans two columns while it has flags so the form has room; read-only for Hiring managers. Saving refreshes the profile, so the header's "Flagged · {n} to review" badge and the Advance gate (`!flagged`) follow. Errors show in the form.
4. **Candidates tab row menu**: "Review flag" opens the profile at the integrity card (`#integrity`).
5. Tests: API (resolve, overlay clears only after the last flag, note rule, audit row, roles, departments, other workspace 404), web helpers (form rules, row states, menu href). Hand-check at 360, 768, 1024, 1440, light and dark.

## Log
- 2026-10-13: Branch `feature/asmt-003-5mswxv` from `develop`. Plan auto-approved (owner's standing rule: no plan approvals). Default picked: the note is required only for Concern confirmed.
- 2026-10-13: Built and checked by hand on the seed (Nicole Aquino with a second flag added locally; Gabriel Mendoza from the Candidates tab's Review flag) at 360, 768, 1024 and 1440 px, light and dark, as Dana (Admin) and Jomar (Hiring manager, read only). Reviewing both flags cleared `has_open_flags` and wrote two `integrity_flag.resolved` audit rows. With flags the integrity card moves up under the score and spans the page; without, it stays in the bottom row. The kit `SegmentedControl` now gives the first segment the Tab stop when nothing is chosen. No migration.

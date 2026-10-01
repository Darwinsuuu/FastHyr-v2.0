# MSG-001: Email templates model and defaults

| Field | Value |
|---|---|
| Epic | MSG — Candidate emails |
| Milestone | M3 Intake |
| Status | Ready |
| Size | M |
| Depends on | [FND-010](../FND/FND-010-email-infrastructure-resend.md), [AUTH-003](../AUTH/AUTH-003-workspaces-create-join-by-code-select-switch.md) |
| Requirements | FR-MSG-01, FR-MSG-03 |
| Gap areas | G5 |
| Design | Frames EmailTemplates, EditEmailTemplate + A-07 |
| Docs to read | [`architecture/NOTIFICATIONS.md §1–3`](../../architecture/NOTIFICATIONS.md), [`design/VOICE_AND_TONE.md`](../../design/VOICE_AND_TONE.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Every workspace starts with warm, ready-to-use templates for each candidate email.

## Scope
**In:**
- `email_templates`, `email_template_versions` migrations
- Default template content for all 9 keys (written to VOICE_AND_TONE)
- Seeding on workspace creation; parameter validation; `[Review.link]` enforcement

**Out:**
- Editor UI (MSG-002)

## Acceptance criteria
- [ ] New workspace has 9 templates
- [ ] Unknown parameters rejected
- [ ] Rejection templates always render the review line
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Create the defaults for new workspaces in `create_default_email_templates()` (`app/services/workspaces.py`, called by `POST /workspaces` since AUTH-003), and backfill workspaces created before this task.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_

# APPLY-004: Apply edge cases and states

| Field | Value |
|---|---|
| Epic | APPLY — Apply |
| Milestone | M3 Intake |
| Status | Backlog |
| Size | S |
| Depends on | [APPLY-003](../APPLY/APPLY-003-application-submission-and-credit-use.md) |
| Requirements | FR-APPLY-05, FR-APPLY-06, FR-APPLY-07 |
| Gap areas | G1 |
| Design | Frame Apply |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Every unusual situation on the apply page has a clear, kind message.

## Scope
**In:**
- Already applied (shows status text)
- Pipeline paused/closed between page load and submit
- Upload failures and retry
- Large/invalid PDF messages
- Signed in as a TA member of the same workspace (allowed, warned)

**Out:**
- —

## Acceptance criteria
- [ ] No credit used on any failed submit
- [ ] Messages follow VOICE_AND_TONE
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_

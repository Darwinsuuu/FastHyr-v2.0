# ASMT-008: Human review requests

| Field | Value |
|---|---|
| Epic | ASMT — Assessment & review |
| Milestone | M5 Review |
| Status | Backlog |
| Size | M |
| Depends on | [ASMT-007](../ASMT/ASMT-007-advance-and-reject-actions.md), [SCREEN-003](../SCREEN/SCREEN-003-post-screen-actions-invite-or-schedule-rejection.md) |
| Requirements | FR-COMP-03 |
| Gap areas | G2, G5 |
| Design | S-03 + A-03 |
| Docs to read | [`decisions/ADR-015-automated-decisions-human-review.md`](../../decisions/ADR-015-automated-decisions-human-review.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Candidates can ask a person to review an automated rejection, and TA teams resolve it.

## Scope
**In:**
- `human_review_requests` migration (requests point at the `review_links` row SCREEN-003 created with the rejection email; look the token up by hash there)
- `/review-request/[token]` page
- Owner notification + candidate acknowledgement emails
- Filter/badge/banner and resolve actions (uphold/override)

**Out:**
- —

## Acceptance criteria
- [ ] Override re-enters the correct stage and sends the right email
- [ ] Link valid 30 days
- [ ] All resolutions audited
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

# DASH-002: Getting started

| Field | Value |
|---|---|
| Epic | DASH — Dashboard |
| Milestone | M6 Billing & analytics |
| Status | Backlog |
| Size | S |
| Depends on | [DASH-001](../DASH/DASH-001-app-shell.md), [WS-001](../WS/WS-001-company-profile.md), [WS-004](../WS/WS-004-member-invites.md), [MSG-002](../MSG/MSG-002-email-templates-list-and-editor.md), [BILL-004](../BILL/BILL-004-subscribe-and-change-plan.md), [PIPE-003](../PIPE/PIPE-003-new-pipeline-wizard-scoring-schedule-credits-revie.md) |
| Requirements | FR-DASH-01 |
| Gap areas | — |
| Design | Frame GettingStarted + A-08 |
| Docs to read | [`design/SCREEN_SPECS.md A-08`](../../design/SCREEN_SPECS.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
New workspaces see a checklist that reflects real progress.

## Scope
**In:**
- Checklist with derived completion and skip state
- Welcome video/tutorial placeholders (OQ-6)
- Demo card

**Out:**
- —

## Acceptance criteria
- [ ] Steps tick automatically from data
- [ ] Copy per A-08
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Replaces the AUTH-003 placeholder at app `/getting-started` (`app/ta/getting-started/`), where new workspaces open.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_

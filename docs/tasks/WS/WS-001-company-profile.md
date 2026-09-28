# WS-001: Company profile

| Field | Value |
|---|---|
| Epic | WS — Workspace admin |
| Milestone | M1 Access |
| Status | Backlog |
| Size | M |
| Depends on | [DASH-001](../DASH/DASH-001-app-shell.md), [FND-011](../FND/FND-011-storage-service-and-pdf-handling.md) |
| Requirements | FR-WS-01 |
| Gap areas | G5 |
| Design | Frame CompanyProfile |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Admins set the employer brand shown on apply pages, interviews and emails.

## Scope
**In:**
- Form + validation
- Logo/banner upload via signed URL with type/size/dimension checks; SVG sanitise/rasterise
- Branding proxy route for emails
- `GET/PUT /workspace/company-profile`

**Out:**
- —

## Acceptance criteria
- [ ] Saved profile appears on apply page and email layout
- [ ] About limited to 600 chars with counter
- [ ] Admin only
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

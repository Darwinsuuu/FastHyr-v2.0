# COMP-002: Notices and consent versioning

| Field | Value |
|---|---|
| Epic | COMP — Compliance |
| Milestone | M3 Intake |
| Status | Ready |
| Size | S |
| Depends on | [FND-004](../FND/FND-004-api-skeleton-auth-request-context-permissions-erro.md) |
| Requirements | FR-COMP-01 |
| Gap areas | G2, G7 |
| Design | Frames Apply, DemoDeviceCheck + S-01 |
| Docs to read | [`compliance/PRIVACY.md §3`](../../compliance/PRIVACY.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Candidate notices and consents are versioned texts, shown consistently and stored with each record.

## Scope
**In:**
- `app/compliance/notices/` versioned texts + API to fetch current versions
- Web components rendering them
- Storage of version + timestamp on application/interview

**Out:**
- —

## Acceptance criteria
- [ ] Changing a text requires a new version
- [ ] Records keep the version they agreed to
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

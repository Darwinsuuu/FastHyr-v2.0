# REL-002: Security review

| Field | Value |
|---|---|
| Epic | REL — Release |
| Milestone | M8 Launch readiness |
| Status | Backlog |
| Size | M |
| Depends on | [REL-001](../REL/REL-001-end-to-end-test-suite.md) |
| Requirements | NFR-01, NFR-02 |
| Gap areas | G7 |
| Design | — |
| Docs to read | [`architecture/SECURITY.md`](../../architecture/SECURITY.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
The MVP passes a structured security review before real candidate data arrives.

## Scope
**In:**
- Review against SECURITY.md and OWASP ASVS L2 checklist
- Dependency and secret scans
- Rate-limit and bot-protection verification
- Fix or ticket every finding

**Out:**
- —

## Acceptance criteria
- [ ] No open high/critical findings
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

# FND-011: Storage service and PDF handling

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | Backlog |
| Size | M |
| Depends on | [FND-004](../FND/FND-004-api-skeleton-auth-request-context-permissions-erro.md) |
| Requirements | NFR-02 |
| Gap areas | — |
| Design | — |
| Docs to read | [`architecture/STORAGE.md`](../../architecture/STORAGE.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Files move between browser and Supabase Storage only through permission-checked signed URLs, and uploaded PDFs are validated and sanitised.

## Scope
**In:**
- Buckets (resumes, recordings, branding, reports, demo) created by migration/config
- `integrations/storage.py`: signed upload/download URLs, move, delete
- PDF validation (magic bytes, size, pages, encryption) and pikepdf sanitising
- Orphan reconciliation cron

**Out:**
- —

## Acceptance criteria
- [ ] Signed URLs expire ≤ 15 min
- [ ] Malformed/encrypted PDFs rejected with clear error codes
- [ ] Sanitised PDF has no JS/embedded files (test fixture)
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Unit tests with PDF fixtures

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_

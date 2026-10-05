# INTV-006: Recording capture and finalisation

| Field | Value |
|---|---|
| Epic | INTV — AI interview |
| Milestone | M4 AI interview |
| Status | Ready |
| Size | L |
| Depends on | [INTV-005](../INTV/INTV-005-live-interview-ui-client.md), [FND-011](../FND/FND-011-storage-service-and-pdf-handling.md) |
| Requirements | FR-INTV-05 |
| Gap areas | — |
| Design | — |
| Docs to read | [`architecture/MEDIA.md §3`](../../architecture/MEDIA.md), [`architecture/STORAGE.md`](../../architecture/STORAGE.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Every interview is recorded safely, even if the connection drops, and turned into one playable file.

## Scope
**In:**
- `recording_chunks`, `interview_attempts` migrations
- Composite stream + MediaRecorder + chunk uploader with retry
- Chunk URL batches + registration endpoints
- `finalize_recording` job (ffmpeg remux, audio extract, poster)
- Upload-progress on end screen (S-02)

**Out:**
- —

## Acceptance criteria
- [ ] Killing the tab loses ≤ 10 s
- [ ] Safari produces playable MP4
- [ ] Chunks deleted after finalise
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

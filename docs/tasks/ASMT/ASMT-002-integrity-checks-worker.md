# ASMT-002: Integrity checks (worker)

| Field | Value |
|---|---|
| Epic | ASMT — Assessment & review |
| Milestone | M5 Review |
| Status | Done |
| Size | L |
| Depends on | [INTV-008](../INTV/INTV-008-authoritative-transcription.md) |
| Requirements | FR-ASMT-06 |
| Gap areas | G7 |
| Design | — |
| Docs to read | [`decisions/ADR-016-integrity-checks-scope.md`](../../decisions/ADR-016-integrity-checks-scope.md), [`architecture/MEDIA.md §5`](../../architecture/MEDIA.md), [`compliance/FRAUD_INTEGRITY.md`](../../compliance/FRAUD_INTEGRITY.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Possible impersonation is flagged at exact moments for human review — never as an automatic rejection.

## Scope
**In:**
- `integrity_flags` migration
- Frame sampling + local face embeddings (same face, no face)
- Second voice from diarisation
- Read-aloud/timing features + model judgement
- Respect biometric consent and pipeline toggle

**Out:**
- —

## Acceptance criteria
- [x] No embeddings persisted
- [x] Flags carry times and confidence
- [x] Pipeline toggle off → no checks
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Fixtures with synthetic media

## Implementation plan
_(Auto-approved per the owner's rule: plans are written here and built without a sign-off.)_

1. **Migration `integrity_flags`** (expand-only): the table as DATABASE.md, with `detail jsonb` (numbers, and the model's one-sentence rationale for `read_aloud`), `confidence numeric(3,2)` 0–1, `status` `open|no_concern|concern_confirmed` (resolved fields set exactly when not open), an index on open flags for the Flagged filter; deleted with the application. `interviews.integrity_status` (`none|ready|off|failed`), `integrity_checks jsonb` (which checks ran, so the profile can say "Face check not run") and `integrity_checked_at`. RLS on, no grants to public keys.
2. **Job `check_integrity(workspace_id, interview_id)`** (`app/jobs/integrity.py`, `services/integrity.py`): queued by `transcribe_interview` next to `score_interview`, and by `requeue_stuck_work` for transcripts unchecked after 10 minutes. Pipeline toggle off → `integrity_status = off`, nothing runs. 3 tries; the failure hook sets `failed`. Flags never move the application.
3. **Same face** (`app/integrity/faces.py`): video interviews with biometric consent only. The recording is streamed to a temp folder; ffmpeg pipes one scaled frame every 2 s straight into memory; OpenCV's YuNet detector and SFace recogniser (MIT / Apache-2.0 weights committed in `app/integrity/weights/`, run locally on the CPU) give the largest face's embedding. Reference = medoid of the first 60 s faces; `different_face` after 3 samples in a row under SFace's 0.363 cosine threshold; `no_face` for 20 s or more. Embeddings live only in memory for the job.
4. **Second voice** (`app/integrity/speech.py`): transcript lines the diariser gave to a third voice (`other`), joined across gaps up to 2 s, flagged from 3 s of speech.
5. **Timing**: each answer's delay after the question (not across a reconnect); outliers above the session median + max(3 scaled MADs, 4 s) and at least 6 s; two or more → one `unusual_timing` flag listing them.
6. **Read aloud**: answers after a long pause (≥ 4 s and 2.5× the median) that are long (≥ 40 words), with few fillers and an even pace go (at most 6, masked) to `integrity_read_aloud@v1`, which judges each window; flag at confidence ≥ 0.6. A model that fails twice leaves just that check `failed`.
7. **Logging**: each flag gets an append-only `ai_decisions` row (`integrity_flag`, numbers only, no rationale). Thresholds live in `app/integrity/config.py` (`integrity_rules@v1`).
8. **Docs**: DATABASE.md, MEDIA.md §5, AI_PIPELINE.md §5, BACKEND.md, ARCHITECTURE.md, FRAUD_INTEGRITY.md §5, AGENTS.md status, BOARD.md (ASMT-002 Done; COMP-001 Ready).

**Not here:** resolving flags and the Flagged filter UI (ASMT-003), showing flags and "Face check not run" on the profile (ASMT-004/006), frame thumbnails on demand. No UI, so the responsive criterion doesn't apply.

**Tests:** unit tests for the face analysis (synthetic embeddings) and the real model loading, second voice, timing, read-aloud windows and the judgement's retry; integration tests through the worker with a synthetic colour-scene recording and a colour face model (all five flag types with times and confidence, toggle off, no biometric consent, repeat, sweeper); `tests/ai_eval` read-aloud cases with a native / non-native pair, run by the owner with a key.

## Log
- 2026-10-09: branch `feature/asmt-002-integrity-checks-rfi393`. Plan auto-approved (owner's rule).
- Face model choice: OpenCV Model Zoo YuNet (MIT) + SFace int8 (Apache-2.0), run through `opencv-python-headless` (4.x). Both are free for commercial use, small (0.2 MB + 9.9 MB, committed with checksums) and CPU-only, so the worker needs no GPU and no download at start. The heavier options (InsightFace, dlib) were ruled out by licence or build size.
- Hand test: a synthetic webcam video made from a public group photo (the candidate's face for 70 s, an empty frame for 24 s, another person for 10 s, the candidate again) gave exactly a `no_face` flag at 01:10–01:34 and a `different_face` flag at 01:34–01:44 (similarity 0.25 vs threshold 0.363; the candidate stayed at 0.99). Scanning the 2-minute video took 1.5 s. The photo is not committed; the integration tests use colour scenes and a colour face model instead.
- Decisions taken without asking: checks run next to scoring rather than after it (they don't depend on each other and nothing waits on them); a failed read-aloud judgement keeps the other flags; `unusual_timing` is one flag per interview listing the late answers; flags start `open` and never move the application.
- Not checked here (no OpenAI key in the cloud container): `tests/ai_eval/test_integrity_read_aloud.py` (a read-aloud textbook answer is flagged; the same spoken story in native and non-native phrasing is not). The owner runs it with a key. Owner check on dev: the worker's memory with OpenCV loaded on a real 30-minute video interview.

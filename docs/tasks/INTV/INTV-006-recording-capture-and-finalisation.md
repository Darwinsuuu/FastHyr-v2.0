# INTV-006: Recording capture and finalisation

| Field | Value |
|---|---|
| Epic | INTV — AI interview |
| Milestone | M4 AI interview |
| Status | Done |
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
- [x] Killing the tab loses ≤ 10 s — hand test: tab closed 22.7 s after the connection came up, 20 s recorded (5 s chunks: at most the open chunk plus one uploading)
- [ ] Safari produces playable MP4 — the server side is tested with Safari-shaped fragmented MP4 chunks (`tests/unit/test_recording.py`, `test_recordings.py`); a run in real Safari needs the owner (no WebKit in the cloud container)
- [x] Chunks deleted after finalise
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
**Database** (expand-only migration). `recording_chunks` as in DATABASE.md (`id`, `workspace_id`, `interview_id`, `attempt_id`, `seq`, `path`, `bytes`, `uploaded_at`; unique `(attempt_id, seq)`; deleted with the interview; RLS on, no grants). `interview_attempts` gains `recording_type` (`webm|mp4`, set by the first chunk URL request) and `recording_stopped_at` (the browser registered the attempt's last chunk). The `recordings` bucket also allows `video/mp4` (Safari).

**Browser** (`lib/interview/recorder.ts`, `uploader.ts`). Each attempt records from the moment its connection is up until it ends: one `MediaStream` with the camera track (video interviews) and a Web Audio mix of the microphone and the interviewer's audio (`MediaStreamAudioDestinationNode`). `MediaRecorder` picks `video/webm;codecs=vp9,opus` → `vp8,opus` → `video/webm` → `video/mp4` (Safari), or the audio-only equivalents for voice-only interviews, at ~1 Mbps video / 64 kbps audio, with a **5 s timeslice** (MEDIA.md says 10 s; with 10 s a killed tab can lose the open chunk plus the one uploading, over the 10 s limit). One uploader per interview, shared across attempts: it asks for signed URLs in batches (`POST …/chunk-urls`, 24 at a time, more when 12 are left), uploads each chunk the moment it exists, retries with backoff (1 s doubling to 30 s, forever while the page is open; "already exists" counts as uploaded), then registers it (`POST …/chunks`). Mute silences the mic in the mix. The live stage warns "Your connection is slow. We're still saving your interview." when more than 60 s of recording waits; leaving asks first while anything waits. After the session ends, the S-02 progress ("Saving your interview… {n}%", "Please keep this page open for a moment.") shows until every chunk is saved, then the link page refreshes as before. The fake connection (`AI_FAKE`) records the microphone (and camera) only; the dev preview's fake API accepts the uploads in memory.

**API** (`services/recordings.py`, candidate routes, same link and account checks as the session routes). `POST /v1/candidate/interviews/{token}/chunk-urls {attempt_id, type, from_seq, count≤30}` → signed upload URLs for `{workspace_id}/{interview_id}/chunks/{attempt_id}/{seq:05d}.{webm|mp4}`. `POST …/chunks {attempt_id, seq, last}` checks the object in Storage (missing → `422 recording_chunk_missing`, over 50 MB → deleted and `422 recording_chunk_too_large`), stores the row (a repeat is fine), sets `recording_status = uploading`, and with `last` sets `recording_stopped_at`. Both answer `409 recording_finalized` once finalising began. URLs are not in the session start response (STORAGE.md): signing 24 URLs would delay the interviewer's first words, so the browser asks right after the connection is up.

**Finalising** (`finalize_recording` job, `app/interview/recording.py` for ffmpeg). Due once the interview is complete and every attempt is settled: its last chunk was registered, or nothing arrived for 2 minutes after it ended; at the latest 30 minutes after completion. The last chunk's registration queues it at once; an every-minute cron `finalize_recordings` queues the rest (and any whose enqueue Redis lost). The job sets `finalizing`, downloads each attempt's chunks from the Storage folder (so a chunk uploaded but never registered still counts) to a temp folder, joins them byte for byte (MediaRecorder chunks are one stream), remuxes each attempt with ffmpeg (`-c copy`; an attempt that can't be read is skipped), concatenates the attempts (copy; re-encode to H.264/AAC MP4 only if they can't be joined as they are, e.g. a different browser on resume), and uploads `recording.webm|mp4` (MP4 with faststart), `audio.m4a` (mono AAC for INTV-008) and `poster.jpg` (video only) with a streaming upload. Then `recording_path`, `duration_seconds`, `recording_status = ready`, chunk rows deleted, commit, and the chunk objects deleted (a retry repeats only the clean-up). Nothing usable, or the last try failing → `failed`. ffmpeg comes from the `imageio-ffmpeg` wheel (a static binary, so the Render Python runtime needs no system package); `FFMPEG_PATH` overrides it.

**Tests** (after hand-testing): integration tests for the chunk endpoints (wrong attempt, missing object, repeat, finalised) with a tenancy case, the due query and the job against fake Storage with real ffmpeg (WebM split into chunks, a fragmented MP4 like Safari's, two attempts, a gap, chunk clean-up); vitest for the uploader (retry, batches, progress, "already exists") and the recorder's type choice.

**Docs** — MEDIA.md §3, STORAGE.md, DATABASE.md, API.md, SCREEN_SPECS S-02 note, AGENTS.md status, BOARD.md.

**Needs the owner** — a Safari run (no WebKit in the cloud container) and a live interview with real OpenAI; hosted Storage must allow files up to the final size (free plan: 50 MB, a 30-minute video is ~150–250 MB), already on the launch list.

## Log
- 2026-10-05: branch `feature/intv-006-interview-recording-nvm38a`. Plan auto-approved (owner's standing rule: no plan approvals).
- Built as planned. Deviations from the docs, all recorded there: 5 s chunks instead of 10 s (MEDIA.md §3); chunk URLs from `…/chunk-urls` right after the connection is up instead of in the session start response (STORAGE.md), so the interviewer's first words aren't delayed; `interview_attempts` already existed (INTV-004), so this task adds two columns to it.
- Hand-tested against the local API (`AI_FAKE=1`), worker and Storage with Chromium's fake camera and microphone: a full video interview (25 s → `recording.webm` 25 s, VP9/Opus, `audio.m4a`, `poster.jpg`, chunks gone), a closed tab then a resume (20 s + 15 s → one 35 s recording), uploads blocked for 70 s (the "connection is slow" note, then "Saving your interview… 0%" until they went through), a voice-only interview (`audio/webm`, no poster) and an interview with no chunks (`failed` after the quiet spell).
- ffmpeg comes from the `imageio-ffmpeg` wheel (static ffmpeg 7.0.2 with libx264, libvpx, libopus and AAC), so Render's Python runtime needs nothing extra.
- Still for the owner: a run in Safari (macOS and iOS) and a live interview against OpenAI, which also checks the interviewer's voice is in the recording (the `AI_FAKE` conversation has no audio). Hosted Storage's global file limit must be raised before real interviews: the Free plan's 50 MB is below a 30-minute recording.
- INTV-008 and INTV-009 are Ready.

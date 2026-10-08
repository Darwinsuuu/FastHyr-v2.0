# INTV-008: Authoritative transcription

| Field | Value |
|---|---|
| Epic | INTV — AI interview |
| Milestone | M4 AI interview |
| Status | Done |
| Size | M |
| Depends on | [INTV-006](../INTV/INTV-006-recording-capture-and-finalisation.md) |
| Requirements | FR-ASMT-01 |
| Gap areas | — |
| Design | Frame CandidateProfile (transcript) |
| Docs to read | [`architecture/MEDIA.md §4`](../../architecture/MEDIA.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Each interview has an accurate, timestamped, speaker-separated transcript that scoring and review rely on.

## Scope
**In:**
- `transcript_segments` migration + full-text index
- `transcribe_interview` job (splitting, diarisation, speaker mapping, topic alignment)

**Out:**
- —

## Acceptance criteria
- [x] Segments ordered with correct timestamps
- [x] Speaker mapping correct on fixtures
- [x] Third speaker preserved as `other`
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md)): not applicable, no screen in this task
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Auto-approved per the owner's rule: plans are written here and built without a sign-off.)_

**What the transcript needs that nothing records yet.** Mapping speakers "by AI response text and timing" and aligning topics "by `set_topic` times" need a timeline of the live call, and the recording needs to say where each attempt sits in it. So:

1. **Migration `transcripts`** (expand-only):
   - `interview_events`: what the sideband saw during an attempt, on the server clock: `kind` `ai_speech` (`at` = the interviewer's audio started, `ended_at` = stopped, `text` = its own response transcript, `ref` = response id) and `topic` (`at`, `topic_index` 0-based). Deleted with the interview. Only the interviewer's words are stored; nothing the candidate says.
   - `interview_attempts.recording_offset_ms`, `recording_ms`: where the attempt sits in the final recording (null = left out of it). Written by `finalize_recording`.
   - `interviews.transcript_status` (`none|processing|ready|failed`), `transcribed_at`.
   - `transcript_segments` as DATABASE.md, plus `seq` (order, unique per interview); GIN full-text index on `to_tsvector('english', text)`; index `(interview_id, start_ms)`. RLS on, no grants to public keys.
2. **Sideband** (`app/interview/sideband.py`): writes an `ai_speech` row per interviewer response (start from `output_audio_buffer.started`, else its first transcript delta; end from `output_audio_buffer.stopped`; text from `response.output_audio_transcript.done`) and a `topic` row per accepted `set_topic`.
3. **Finalize** (`app/interview/recording.py`, `services/recordings.py`): `build()` reports each kept attempt's offset and length; `finalize()` stores them, and the job queues `transcribe_interview` when the recording is `ready`.
4. **Transcription client** (`app/ai/transcription.py`): `Transcriber` protocol; `OpenAITranscriber` calls `audio.transcriptions.create` with `OPENAI_TRANSCRIBE_MODEL` (`gpt-4o-transcribe-diarize`), `response_format=diarized_json`, `chunking_strategy=auto`; one `ai_calls` row per piece (`interview_transcription`, `transcription@v1`, audio seconds, cost from `OPENAI_PRICES`: token prices, or `per_minute`). `FakeTranscriber` under `AI_FAKE=1` answers from `fixtures/transcription@v1.json`, spread over the piece's length. No prompt is sent (the diarising model takes none), so the version names the request settings.
5. **Transcript logic** (`app/interview/transcript.py`, pure functions):
   - *Splitting:* audio ≤ 10 minutes is one piece; longer audio is cut at the middle of a silence (ffmpeg `silencedetect`) between 5 and 10 minutes into each piece, or hard at 10 minutes if there is none; each piece carries 2 s of overlap on both sides, and a segment belongs to the piece whose own range holds its midpoint.
   - *Speakers, per piece* (the diariser's labels A, B… don't carry across pieces): the label whose segments best match the interviewer's own words (share of a segment's words found in a nearby `ai_speech` text) and overlap its speaking times is `interviewer`; of the rest, the label with the most speech is `candidate`; every other label is `other`. A segment of another label whose words are the interviewer's and whose midpoint falls inside an interviewer speaking time is moved to `interviewer` (the diariser merged them). With no events at all (a failed sideband): the first piece's first speaker is the interviewer (it always opens), later pieces take the label asking most questions.
   - *Recording time* of a server time in an attempt: `recording_offset_ms + (t − connected_at)` (the browser starts recording when its connection is up, the moment of its first heartbeat).
   - *Topics:* each attempt starts on `resume_from`; a `topic` event moves the topic from the first interviewer segment that starts at or after one second before it, so a question lands in the topic it opens; candidate segments follow the topic in force.
6. **Job** `transcribe_interview(workspace_id, interview_id)` (`app/jobs/transcripts.py`, service `services/transcripts.py`): skips unless the recording is ready and the transcript isn't; sets `processing`, downloads `audio.m4a`, splits, transcribes, maps, replaces the interview's segments and sets `ready` in one transaction. Retries 4 times with backoff; the failure hook sets `failed`. `requeue_stuck_work` re-queues ready recordings whose transcript is still `none`/`processing` 10 minutes after the interview completed. ASMT-001 queues scoring after it.
7. **Docs:** MEDIA.md §4 as built, DATABASE.md, BACKEND.md, DEPLOYMENT.md (`OPENAI_TRANSCRIBE_MODEL` on API and worker), render.yaml, AGENTS.md status, BOARD.md (INTV-008 Done; ASMT-001 and ASMT-002 Ready).

**Not here:** the transcript endpoint and search UI (ASMT-006), scoring (ASMT-001), `second_voice` flags from `other` segments (ASMT-002). There is no UI, so the responsive criterion doesn't apply.

**Tests:** unit tests for splitting, merging, speaker mapping (fixtures with a two-person call, a third voice, a merged label, no events) and topic alignment; integration tests for the sideband's events, finalize storing offsets and queuing the job, the job end to end on real ffmpeg audio with the fake transcriber, and the requeue.

## Log
- 2026-10-07: branch `feature/intv-008-transcription-obpqh3`. Plan auto-approved (owner's rule).
- Built as planned. Tests: `tests/unit/test_transcript.py` (pieces, merging, speakers incl. third voice, merged label, one-voice piece, no timeline, topics across a resume) and `tests/integration/test_transcripts.py` (finalize → transcribe through the worker, a 700 s file cut at its silence, the failure state, the sideband's timeline, the OpenAI request shape and its `ai_calls` row).
- Not checked here: a real `gpt-4o-transcribe-diarize` run (no OpenAI key in the cloud container). The owner sets `OPENAI_TRANSCRIBE_MODEL` on the worker and checks one real interview's transcript.
- Decision taken without asking: the interviewer's own words (its Realtime response transcript) are stored in `interview_events` to tell its voice apart; nothing the candidate says is stored there.

# Media: device check, live interview, recording, transcription, integrity

## 1. Device check (browser only)
- Request camera (video format) and microphone permission with an explanation shown *before* the browser prompt. Handle denied/blocked with per-browser fix instructions.
- Camera: preview with face outline; on-device face detection (MediaPipe Face Detection, WASM) confirms one face is centred and well lit; "wave" detection = hand/motion in the top-right region (fallback: candidate taps "I can see myself" after 5 s).
- Microphone: level meter via Web Audio `AnalyserNode`; pass when speech-level audio is detected for ≥ 2 s while reading the sentence.
- Device pickers for camera and mic; remember the choice in `localStorage` (try/catch).
- Consent checkbox (FR-INTV-03). No media leaves the browser during the check.
- As built (INTV-003): `lib/interview/devices.ts` (pure helpers) and `components/interview/use-device-check.ts`. MediaPipe (`@mediapipe/tasks-vision`, BlazeFace short range) runs on the CPU in the browser; its WebAssembly files are copied from `node_modules` to `apps/web/public/mediapipe/` by `scripts/copy-mediapipe.mjs` (run by `dev` and `build`) and the model is committed there, so nothing loads from a third party. Frames are read at 64 × 48 every 100 ms for motion and light; faces every 250 ms. The camera passes on a wave in the top right of the mirrored preview with one centred, well-lit face (or the wave alone if the model can't load), or by "I can see myself" after 5 s. The microphone passes after 2 s at or above −38 dBFS; after 20 s without it the card asks the candidate to check their mic. Fix steps for blocked permissions cover Chrome, Edge, Firefox, Safari, iOS Safari, other iOS browsers, Android and in-app browsers. "Start interview" posts the consent and stops the camera and microphone.

## 2. Live interview (OpenAI Realtime over WebRTC)
The API opens every call itself (ADR-021, INTV-004): the browser sends its SDP offer, never holds an OpenAI key, and its audio goes straight to OpenAI.
```
Browser                                  FastAPI (+ worker)                     OpenAI Realtime
  │ RTCPeerConnection: mic track, data channel "oai-events", createOffer()           │
  │ POST /candidate/interviews/{t}/session {sdp}                                     │
  │───────────────────────────────────────▶ │ instructions from plan (interviewer@vN)│
  │                                         │ POST /v1/realtime/calls {sdp, session}▶│
  │                                         │ ◀── SDP answer + call id               │
  │ ◀── {attempt_id, sdp, time_left_seconds, wrap_up_in_seconds, topics[], …}         │
  │ setRemoteDescription(answer) ─────────── ICE / DTLS ────────────────────────────▶ │
  │                                         │ worker: run_realtime_session attaches  │
  │                                         │ the sideband (wss …?call_id=) ────────▶│
  │ ◀─────────────── AI audio + events (captions, speaking state, tool calls) ───── │
  │ heartbeat every 15 s ─────────────────▶ │ talk time on the server clock; at 25 min wrap-up; at 30 min hang up
```
- **Instructions** (`app/ai/interviewer.py`, `prompts/interviewer@vN.md`) and the session config go out when the API creates the call; the sideband applies them again and reverts any `session.update`, system message or typed message the browser sends on its data channel (three of those end the attempt as `error`). It then sends the opening cue so the interviewer speaks first.
- Voice activity detection: server VAD with 1 s of silence before the turn ends, so candidates can pause to think.
- Input audio transcription (`OPENAI_CAPTION_MODEL`) is enabled for **live captions only**; it is not used for scoring.
- Captions: AI speech from response transcripts; candidate speech from input transcription events.
- Tool calls (`set_topic(number)`, 1-based as the topics list; `show_resume_quote(text)`; `end_interview(reason)`) arrive on both the data channel and the sideband. The browser only displays them; **the server answers every tool call** and is authoritative for `end_interview` and time limits.
- **Attempts** (`interview_attempts`): each `/session` call is an attempt with `seconds_allowed` = what is left of the 30-minute cap; it ends at `started_at + seconds_allowed` whatever the browser does. Three layers enforce it: the sideband job hangs up on time (`time_cap`), a heartbeat past the deadline ends it, and the every-minute `end_overdue_attempts` cron ends attempts past their deadline or silent for 60 s.
- **Reconnect:** on ICE failure or page reload the client calls `/session` again; the previous attempt is ended (`disconnect`, or `error` if it never reported a connection) and hung up, and the new attempt's instructions carry a summary of the topics covered and continue from the topic after the furthest one reached (WORKFLOW.md §4). Three attempts that never connected within 5 minutes → `409 interview_technical_issue`, `drop_reason = technical_issue` and the "We couldn't connect you" screen; the link stays valid and the first heartbeat of a later connection clears it.
- **Ending:** "End interview" calls `/complete` (`candidate_ended`); the interviewer's `end_interview` ends it once the goodbye has played (`wrap_up`, or `candidate_ended` when the candidate asked to stop); the cap ends it (`time_cap`). All three complete the interview and move the application to `scoring`. A dropped call leaves it `abandoned` to resume.
- Mute pauses the mic track (`enabled = false`) and shows "Paused — your mic is off" (INTV-005). Nothing is sent to the model: the browser may not add messages (the sideband reverts them as tampering), and with server VAD a silent mic never ends a turn, so the interviewer waits.
- **Client** (INTV-005, `lib/interview/`): the first heartbeat goes out the moment the peer connection reports `connected` (the opening waits for it), then every `heartbeat_seconds`. A connection that fails, stays `disconnected` for 5 s, or isn't up 15 s after the offer is replaced by a new `/session` call (up to 3 in a row, then "We couldn't connect you" with Try again); a `409` (`interview_not_open`, `interview_technical_issue`) or a heartbeat `ended` hands back to the link page, which shows the new state. After the interviewer's `end_interview`, the hang-up ends the session instead of reconnecting. The time from `connected` to the first AI audio is recorded as the performance measure `interview:first-utterance` (target p75 < 1.5 s).
- **Local runs without OpenAI:** under `AI_FAKE=1` the API answers with a fake SDP (`s=fake`); in local and development builds the web then plays a scripted conversation with the same data-channel events (`lib/interview/fake-realtime.ts`). `/dev/interview` on the site host runs the stage against it with a fake API.
- Cost: one `ai_calls` row per sideband run (`interview_realtime`, tokens, `audio_seconds`, cost from `OPENAI_PRICES` with optional `audio_input`/`audio_output` prices).

## 3. Recording
- Compose one `MediaStream`: candidate camera video (if video format) + an audio mix (candidate mic + AI audio) via Web Audio `MediaStreamAudioDestinationNode`.
- `MediaRecorder` with `video/webm;codecs=vp9,opus` (Safari: `video/mp4`), bitrate ~1 Mbps video / 64 kbps audio, `timeslice = 10 s`.
- Each chunk uploads immediately to its signed URL (retry with backoff; queue in memory up to 60 s; warn the candidate if uploads fall behind).
- `/complete` (or server-side end) → worker `finalize_recording`: concatenate chunks per attempt (ffmpeg remux, no re-encode when possible), join attempts, produce `recording.webm|mp4`, `audio.m4a` (for transcription) and a poster frame; delete chunks after success.
- Voice-only interviews record audio only.
- As built (INTV-006): `lib/interview/recorder.ts` records each attempt from the moment its connection is up until it ends (one stream per attempt: WebM `vp9,opus` → `vp8,opus` → plain WebM, or MP4 on Safari; `audio/*` for voice-only) with a **5 s timeslice** rather than 10 s, so a closed tab loses the chunk being recorded plus at most one still uploading, under 10 s. The mix is a Web Audio `MediaStreamAudioDestinationNode` fed by the microphone (silent while muted) and the interviewer's track (`onRemoteStream` from `realtime.ts`; the scripted `AI_FAKE` connection has none). `lib/interview/uploader.ts` is one queue for the whole interview: it asks `POST …/chunk-urls` for 24 signed URLs at a time (again when 12 are left), uploads chunks in order, retries with backoff (1 s doubling to 30 s, for as long as the page is open; Storage's "Duplicate" answer counts as uploaded; a chunk refused three times is skipped), registers each with `POST …/chunks`, and after an attempt's recorder stops re-registers its last chunk with `last: true`. Nothing is dropped while uploads fall behind; past 60 s waiting the stage shows "Your connection is slow…", and leaving the page asks first while anything waits. After the session ends, the S-02 progress ("Saving your interview… {n}%") shows until every chunk is saved, then the link page refreshes.
- **Finalising** (`services/recordings.py`, `app/interview/recording.py`, job `finalize_recording`): due once the interview is complete and every attempt is settled (its last chunk registered, or 2 minutes with nothing new after it ended), and at the latest 30 minutes after completion. The last chunk's registration queues it; the every-minute `finalize_recordings` cron queues the rest. Chunks are read from the Storage folder (an uploaded chunk that was never registered still counts), joined byte for byte per attempt, remuxed with `-c copy` (an attempt without its header chunk is left out), and the attempts concatenated without re-encoding when they match, otherwise re-encoded to H.264/AAC MP4. Outputs: `recording.webm|mp4` (MP4 with fast start), `audio.m4a` (mono AAC, 64 kbps) and `poster.jpg` (video only, ≤ 640 px wide). Then `recording_path`, `duration_seconds`, `recording_status = ready`, and the chunks are deleted; nothing usable (or the last try failing) sets `failed` and keeps the chunks. ffmpeg is the static binary from the `imageio-ffmpeg` wheel unless `FFMPEG_PATH` is set, so the Render Python runtime needs no system package.

## 4. Transcription (authoritative)
- `transcribe_interview` sends `audio.m4a` to the OpenAI transcription model with speaker separation (diarisation) and word/segment timestamps; long audio is split on silence into ≤ 10-minute pieces with overlap and merged.
- Speakers are mapped to `interviewer` (matches AI response text/timing), `candidate`, `other`.
- Segments are stored in `transcript_segments`, then topics are aligned using `set_topic` event times.

## 5. Integrity checks (worker, ADR-016)
- **Frames:** ffmpeg samples one frame every 2 s (video format).
- **Faces:** local face-detection + embedding model; reference = embedding cluster from the first 60 s; flag `different_face` when a frame's embedding distance exceeds the threshold for ≥ 3 consecutive samples; flag `no_face` for ≥ 20 s without a face.
- **Voices:** third-speaker segments from diarisation ≥ 3 s → `second_voice`.
- **Read-aloud / timing:** see `AI_PIPELINE.md` §5.
- Embeddings and frames are kept in memory/temp only and deleted after the job. Only flag rows persist.
- Candidates who did not give biometric consent (where required) → face checks skipped; noted on the profile ("Face check not run").

## 6. Demo differences
- Uses the same client code with `mode = demo`: no recording upload, no transcription job, no scoring; 10-minute cap; session data hard-deleted.

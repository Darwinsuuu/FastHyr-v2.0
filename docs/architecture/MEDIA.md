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
- Mute pauses the mic track and tells the model the candidate is muted (status "Paused — your mic is off") (INTV-005).
- Cost: one `ai_calls` row per sideband run (`interview_realtime`, tokens, `audio_seconds`, cost from `OPENAI_PRICES` with optional `audio_input`/`audio_output` prices).

## 3. Recording
- Compose one `MediaStream`: candidate camera video (if video format) + an audio mix (candidate mic + AI audio) via Web Audio `MediaStreamAudioDestinationNode`.
- `MediaRecorder` with `video/webm;codecs=vp9,opus` (Safari: `video/mp4`), bitrate ~1 Mbps video / 64 kbps audio, `timeslice = 10 s`.
- Each chunk uploads immediately to its signed URL (retry with backoff; queue in memory up to 60 s; warn the candidate if uploads fall behind).
- `/complete` (or server-side end) → worker `finalize_recording`: concatenate chunks per attempt (ffmpeg remux, no re-encode when possible), join attempts, produce `recording.webm|mp4`, `audio.m4a` (for transcription) and a poster frame; delete chunks after success.
- Voice-only interviews record audio only.

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

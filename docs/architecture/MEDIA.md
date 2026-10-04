# Media: device check, live interview, recording, transcription, integrity

## 1. Device check (browser only)
- Request camera (video format) and microphone permission with an explanation shown *before* the browser prompt. Handle denied/blocked with per-browser fix instructions.
- Camera: preview with face outline; on-device face detection (MediaPipe Face Detection, WASM) confirms one face is centred and well lit; "wave" detection = hand/motion in the top-right region (fallback: candidate taps "I can see myself" after 5 s).
- Microphone: level meter via Web Audio `AnalyserNode`; pass when speech-level audio is detected for ≥ 2 s while reading the sentence.
- Device pickers for camera and mic; remember the choice in `localStorage` (try/catch).
- Consent checkbox (FR-INTV-03). No media leaves the browser during the check.
- As built (INTV-003): `lib/interview/devices.ts` (pure helpers) and `components/interview/use-device-check.ts`. MediaPipe (`@mediapipe/tasks-vision`, BlazeFace short range) runs on the CPU in the browser; its WebAssembly files are copied from `node_modules` to `apps/web/public/mediapipe/` by `scripts/copy-mediapipe.mjs` (run by `dev` and `build`) and the model is committed there, so nothing loads from a third party. Frames are read at 64 × 48 every 100 ms for motion and light; faces every 250 ms. The camera passes on a wave in the top right of the mirrored preview with one centred, well-lit face (or the wave alone if the model can't load), or by "I can see myself" after 5 s. The microphone passes after 2 s at or above −38 dBFS; after 20 s without it the card asks the candidate to check their mic. Fix steps for blocked permissions cover Chrome, Edge, Firefox, Safari, iOS Safari, other iOS browsers, Android and in-app browsers. "Start interview" posts the consent and stops the camera and microphone.

## 2. Live interview (OpenAI Realtime over WebRTC)
```
Browser                                  FastAPI                                OpenAI Realtime
  │ POST /candidate/interviews/{t}/session  │                                       │
  │───────────────────────────────────────▶ │ build instructions from plan          │
  │                                         │ create client secret (TTL ~1 min) ───▶ │
  │ ◀── {client_secret, model, time_left, chunk_urls[], attempt_id}                  │
  │ RTCPeerConnection (mic track in, AI audio track out, data channel "oai-events")  │
  │────────────────────────────── SDP offer/answer ────────────────────────────────▶ │
  │                                         │ attach sideband connection (call id) ─▶│
  │ ◀─────────────── AI audio + events (captions, speaking state, tool calls) ───── │
  │ heartbeat every 15 s ─────────────────▶ │ track talk time; at 25 min send wrap-up; at 30 min end
```
- Voice activity detection: server VAD with settings tuned for interviews (longer silence before turn end, ~1 s) so candidates can pause to think.
- Input audio transcription is enabled for **live captions only**; it is not used for scoring.
- Captions: AI speech from response transcripts; candidate speech from input transcription events.
- Tool calls (`set_topic`, `show_resume_quote`, `end_interview`) arrive on the data channel and the sideband; the server is authoritative for `end_interview` and time limits.
- Reconnect: on ICE failure or page reload, the client calls `/session` again; the API creates a new attempt with a resume summary (WORKFLOW.md §4). After 3 failed connects in 5 minutes → `technical_issue` drop reason and a friendly "try again later" screen (link stays valid).
- Mute pauses the mic track and tells the model the candidate is muted (status "Paused — your mic is off").

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

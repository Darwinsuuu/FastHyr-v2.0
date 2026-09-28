# ADR-007: OpenAI for all AI features

- **Status:** Accepted
- **Date:** 2026-09-29

## Decision
- **Live AI interview:** OpenAI **Realtime API** (speech-to-speech). The browser connects over **WebRTC** using a short-lived client secret minted by FastAPI. The API attaches a **server-side (sideband) connection** to the same session where supported, to push instructions, receive events and end the session; it never relays audio.
- **Everything else** — résumé analysis, interview plans, scoring, summaries, integrity analysis of transcripts, Ava — uses OpenAI text models through the **Responses API with structured outputs** (JSON schema).
- **Transcription** of the finished recording (the authoritative transcript used for scoring) uses an OpenAI transcription model with timestamps and speaker separation.
- Model names are configuration (`OPENAI_REALTIME_MODEL`, `OPENAI_TEXT_MODEL`, `OPENAI_TRANSCRIBE_MODEL`), never hard-coded.
- Every AI call records `model`, `prompt_version` and token usage.

## Consequences
- One vendor, one key, one bill. Vendor lock-in is contained behind `app/ai/` interfaces in the API.
- Scoring never depends on transcripts produced in the browser.
- Face checks for integrity (ADR-016) run locally in the worker, not through OpenAI.
- Enterprise customers may ask about OpenAI data use: use API data controls (no training on API data; zero data retention where available) and disclose OpenAI as a sub-processor in the Privacy Policy.

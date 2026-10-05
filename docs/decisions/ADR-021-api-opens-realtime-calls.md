# ADR-021: The API opens live interview calls; the browser gets no OpenAI key

- **Status:** Proposed (amends ADR-007's client-secret line)
- **Date:** 2026-10-05
- **Deciders:** Darwin (product owner), proposed by Claude in INTV-004

## Context
ADR-007 says the browser connects to OpenAI Realtime over WebRTC with a short-lived client secret minted by FastAPI, and the API attaches a sideband connection to the same session. With a client secret the browser opens the call itself, so the API learns the call id only if the browser reports it. A tampered browser could skip that and keep the call open past the 30-minute cap (ADR-012) up to OpenAI's own session limit, and INTV-004 requires that the cap holds even if the client misbehaves. Session settings attached to a client secret can also be overridden by the client when it connects.

## Options considered
1. **Client secret (ADR-007 as written)** — the browser posts its SDP offer to OpenAI with the secret. Simple, but the API can enforce the cap only on calls the browser tells it about.
2. **API opens the call** — the browser sends its SDP offer to `POST /v1/candidate/interviews/{token}/session`; the API posts it to OpenAI's `POST /v1/realtime/calls` with the server key and the full session config and returns the SDP answer. Audio still flows directly between the browser and OpenAI. The API knows every call id, so it can attach the sideband and hang up (`POST /v1/realtime/calls/{id}/hangup`) whatever the browser does. One extra hop (~100 ms) at connection time only.

## Decision
Option 2. The browser never receives an OpenAI key or client secret. The API creates each call with the browser's offer, attaches the sideband with the call id, and is the only party that can end the call early or at the cap. The sideband re-applies the instructions if the browser changes them through the data channel. The API never relays audio.

## Consequences
- MEDIA.md §2 and API.md describe `POST …/session {sdp}` → `{sdp, attempt_id, …}` instead of a client secret.
- The cap is enforced in three places: the sideband job hangs up on time, a heartbeat past the deadline ends the attempt, and an every-minute watchdog ends attempts past their deadline or without heartbeats.
- The public demo (INTV-010) should open its calls the same way.
- ADR-007 stays Accepted for everything else; its "short-lived client secret" sentence is superseded by this ADR once accepted.

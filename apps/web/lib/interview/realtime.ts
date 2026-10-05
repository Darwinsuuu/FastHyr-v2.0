// The live interview's connection to OpenAI Realtime over WebRTC (INTV-005, MEDIA.md §2,
// ADR-021). The browser makes the offer, the API opens the call with it and answers; audio then
// flows straight between the browser and OpenAI. The browser reads the data channel's events
// (captions, speaking state, tool calls) and never sends session events or tool answers: the
// server owns the session.

import { startFakeRealtime } from "./fake-realtime";
import { readEvent, type TalkEvent } from "./session";

/** The data channel OpenAI Realtime uses for events. */
export const EVENTS_CHANNEL = "oai-events";

/** What the stage hears about the connection. */
export type LinkState = "connected" | "lost";

export interface RealtimeHandlers {
  onEvent: (event: TalkEvent) => void;
  onState: (state: LinkState) => void;
  /** The interviewer's audio, for the recording (INTV-006). */
  onRemoteStream?: (stream: MediaStream) => void;
}

export interface RealtimeConnection {
  /** Pauses or resumes the microphone track (nothing is sent while paused). */
  setMuted: (muted: boolean) => void;
  close: () => void;
}

/** The SDP answer `FakeRealtime` gives under the API's `AI_FAKE=1` (apps/api app/ai/realtime.py). */
export function isFakeAnswer(sdp: string): boolean {
  return /^s=fake\r?$/m.test(sdp);
}

/** A connection that stays "disconnected" this long is treated as lost. */
export const DISCONNECTED_GRACE_MS = 5000;

/**
 * Connects the microphone to a new Realtime call. `openCall` posts the offer to the API and
 * returns its answer. Rejects when the offer or answer fails; later problems arrive as a "lost"
 * state. With `allowFake`, an `AI_FAKE` answer plays a scripted conversation instead (local and
 * development only).
 */
export async function connectRealtime({
  stream,
  openCall,
  handlers,
  allowFake,
}: {
  stream: MediaStream;
  openCall: (offer: string) => Promise<string>;
  handlers: RealtimeHandlers;
  allowFake: boolean;
}): Promise<RealtimeConnection> {
  const mic = stream.getAudioTracks()[0];
  if (!mic) throw new Error("No microphone track");

  const pc = new RTCPeerConnection();
  const audio = new Audio();
  audio.autoplay = true;
  let closed = false;
  let graceTimer: ReturnType<typeof setTimeout> | undefined;
  let reported: LinkState | null = null;

  const report = (state: LinkState) => {
    if (closed || reported === state) return;
    // "lost" is final for this connection: the session makes a new one.
    if (reported === "lost") return;
    reported = state;
    handlers.onState(state);
  };

  pc.ontrack = (event) => {
    const remote = event.streams[0] ?? new MediaStream([event.track]);
    audio.srcObject = remote;
    handlers.onRemoteStream?.(remote);
    void audio.play().catch(() => {
      // Autoplay is allowed after the Start tap; if a browser still refuses, captions carry on.
    });
  };
  pc.addTrack(mic, stream);

  const channel = pc.createDataChannel(EVENTS_CHANNEL);
  channel.onmessage = (message) => {
    if (typeof message.data !== "string") return;
    let parsed: unknown;
    try {
      parsed = JSON.parse(message.data);
    } catch {
      return;
    }
    const event = readEvent(parsed);
    if (event) handlers.onEvent(event);
  };
  channel.onclose = () => report("lost");

  pc.onconnectionstatechange = () => {
    clearTimeout(graceTimer);
    switch (pc.connectionState) {
      case "connected":
        report("connected");
        break;
      case "disconnected":
        // Often a brief network blip that heals by itself.
        graceTimer = setTimeout(() => report("lost"), DISCONNECTED_GRACE_MS);
        break;
      case "failed":
      case "closed":
        report("lost");
        break;
    }
  };

  const close = () => {
    if (closed) return;
    closed = true;
    clearTimeout(graceTimer);
    channel.onclose = null;
    pc.onconnectionstatechange = null;
    channel.close();
    pc.close();
    audio.srcObject = null;
  };

  try {
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    const answer = await openCall(offer.sdp ?? "");
    if (allowFake && isFakeAnswer(answer)) {
      close();
      return startFakeRealtime({ stream, handlers });
    }
    await pc.setRemoteDescription({ type: "answer", sdp: answer });
  } catch (error) {
    close();
    throw error;
  }

  return {
    setMuted: (muted) => {
      mic.enabled = !muted;
    },
    close,
  };
}

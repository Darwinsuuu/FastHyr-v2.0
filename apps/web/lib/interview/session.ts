// The live interview's state (INTV-005, FRONTEND.md §4, MEDIA.md §2): a pure reducer that turns
// the connection's progress, OpenAI Realtime events from the data channel and the server's
// heartbeats into what the stage shows. `useInterviewSession` (components/interview) drives it.

/** One step of the session. `ended` hands back to the link page, which shows what's next. */
export type SessionPhase = "connecting" | "live" | "reconnecting" | "ending" | "ended" | "failed";

/** Why the session stopped short: the camera or mic, or no connection after several tries. */
export type SessionFailure = "media" | "connect";

/** What the interviewer is doing, for the status line under its name. */
export type InterviewerStatus =
  "connecting" | "reconnecting" | "speaking" | "thinking" | "listening" | "paused" | "ending";

export interface CaptionLine {
  /** The Realtime conversation item id. */
  id: string;
  who: "ai" | "you";
  text: string;
  done: boolean;
}

export interface SessionTopic {
  number: number;
  title: string;
}

/** The parts of the API's session answer the stage needs. */
export interface SessionStart {
  attemptId: string;
  timeLeftSeconds: number;
  topics: SessionTopic[];
  topicNumber: number;
}

/**
 * Data-channel events the stage reads, normalised from OpenAI Realtime server events (GA names,
 * with the beta names some models still send). The browser only reads tool calls: the server
 * answers every one (ADR-021).
 */
export type TalkEvent =
  | { type: "ai_text"; id: string; delta: string }
  | { type: "ai_text_done"; id: string; text: string }
  | { type: "ai_audio"; playing: boolean }
  | { type: "thinking" }
  | { type: "response_done" }
  | { type: "you_started"; id: string }
  | { type: "you_stopped" }
  | { type: "you_text"; id: string; delta: string }
  | { type: "you_text_done"; id: string; text: string }
  | { type: "you_text_failed"; id: string }
  | { type: "topic"; number: number }
  | { type: "quote"; text: string }
  | { type: "end_requested" };

export interface SessionState {
  phase: SessionPhase;
  failure: SessionFailure | null;
  attemptId: string | null;
  topics: SessionTopic[];
  /** The topic being discussed (1-based, as `set_topic`). */
  topicNumber: number;
  /** Seconds left of the 30-minute cap: counted down here, corrected by each heartbeat. */
  secondsLeft: number | null;
  wrapUp: boolean;
  muted: boolean;
  aiSpeaking: boolean;
  youSpeaking: boolean;
  thinking: boolean;
  captions: CaptionLine[];
  /** "From your résumé": held until the interviewer moves on after the candidate's answer. */
  quote: string | null;
  quoteAnswered: boolean;
}

export type SessionAction =
  | { type: "started"; session: SessionStart }
  | { type: "connected" }
  | { type: "connection_lost" }
  | { type: "event"; event: TalkEvent }
  | { type: "tick"; seconds?: number }
  | { type: "heartbeat"; status: "active" | "wrap_up" | "ended"; timeLeftSeconds: number }
  | { type: "mute"; muted: boolean }
  | { type: "ending" }
  | { type: "ended" }
  | { type: "failed"; failure: SessionFailure }
  | { type: "retry" };

export const INITIAL_SESSION: SessionState = {
  phase: "connecting",
  failure: null,
  attemptId: null,
  topics: [],
  topicNumber: 1,
  secondsLeft: null,
  wrapUp: false,
  muted: false,
  aiSpeaking: false,
  youSpeaking: false,
  thinking: false,
  captions: [],
  quote: null,
  quoteAnswered: false,
};

const FINISHED: ReadonlySet<SessionPhase> = new Set(["ended", "failed"]);

export function reduceSession(state: SessionState, action: SessionAction): SessionState {
  if (FINISHED.has(state.phase) && action.type !== "retry") return state;
  switch (action.type) {
    case "started": {
      const { session } = action;
      return {
        ...state,
        attemptId: session.attemptId,
        topics: session.topics,
        // A resumed attempt starts from a later topic; never move the marker backwards.
        topicNumber: Math.max(state.topicNumber, session.topicNumber),
        secondsLeft: session.timeLeftSeconds,
      };
    }
    case "connected":
      return state.phase === "ending" ? state : { ...state, phase: "live" };
    case "connection_lost":
      // Hanging up is how the server ends the call after the goodbye.
      if (state.phase === "ending") return { ...state, phase: "ended" };
      return {
        ...state,
        phase: "reconnecting",
        aiSpeaking: false,
        youSpeaking: false,
        thinking: false,
      };
    case "event":
      return applyEvent(state, action.event);
    case "tick": {
      if (state.secondsLeft === null || (state.phase !== "live" && state.phase !== "ending")) {
        return state;
      }
      return { ...state, secondsLeft: Math.max(0, state.secondsLeft - (action.seconds ?? 1)) };
    }
    case "heartbeat":
      if (action.status === "ended") return { ...state, phase: "ended", secondsLeft: 0 };
      return {
        ...state,
        secondsLeft: action.timeLeftSeconds,
        wrapUp: state.wrapUp || action.status === "wrap_up",
      };
    case "mute":
      return {
        ...state,
        muted: action.muted,
        youSpeaking: action.muted ? false : state.youSpeaking,
      };
    case "ending":
      return { ...state, phase: "ending" };
    case "ended":
      return { ...state, phase: "ended" };
    case "failed":
      return { ...state, phase: "failed", failure: action.failure };
    case "retry":
      return { ...state, phase: "connecting", failure: null };
  }
}

function applyEvent(state: SessionState, event: TalkEvent): SessionState {
  switch (event.type) {
    case "ai_text":
    case "ai_text_done": {
      const existing = state.captions.find((line) => line.id === event.id);
      const text = event.type === "ai_text" ? (existing?.text ?? "") + event.delta : event.text;
      const done = event.type === "ai_text_done";
      // The interviewer moved on after the candidate answered: the old quote goes.
      const newLine = !existing;
      const clearQuote = newLine && state.quoteAnswered;
      return {
        ...state,
        captions: upsert(state.captions, { id: event.id, who: "ai", text, done }),
        thinking: false,
        quote: clearQuote ? null : state.quote,
        quoteAnswered: clearQuote ? false : state.quoteAnswered,
      };
    }
    case "ai_audio":
      return {
        ...state,
        aiSpeaking: event.playing,
        thinking: event.playing ? false : state.thinking,
      };
    case "thinking":
      return { ...state, thinking: true };
    case "response_done":
      return { ...state, thinking: false };
    case "you_started":
      return {
        ...state,
        youSpeaking: true,
        captions: state.captions.some((line) => line.id === event.id)
          ? state.captions
          : [...state.captions, { id: event.id, who: "you", text: "", done: false }],
        quoteAnswered: state.quote !== null,
      };
    case "you_stopped":
      return { ...state, youSpeaking: false };
    case "you_text": {
      const existing = state.captions.find((line) => line.id === event.id);
      return {
        ...state,
        captions: upsert(state.captions, {
          id: event.id,
          who: "you",
          text: (existing?.text ?? "") + event.delta,
          done: false,
        }),
      };
    }
    case "you_text_done": {
      const text = event.text.trim();
      if (!text) return { ...state, captions: state.captions.filter((l) => l.id !== event.id) };
      return {
        ...state,
        captions: upsert(state.captions, { id: event.id, who: "you", text, done: true }),
      };
    }
    case "you_text_failed":
      return {
        ...state,
        captions: state.captions.filter((line) => line.id !== event.id || line.text.trim() !== ""),
      };
    case "topic": {
      const known =
        state.topics.length === 0 || state.topics.some((t) => t.number === event.number);
      return known ? { ...state, topicNumber: event.number } : state;
    }
    case "quote": {
      const text = event.text.trim();
      return text ? { ...state, quote: text, quoteAnswered: false } : state;
    }
    case "end_requested":
      return { ...state, phase: state.phase === "ended" ? state.phase : "ending" };
  }
}

/** Replaces the line with the same id in place, or adds it at the end. */
function upsert(lines: CaptionLine[], line: CaptionLine): CaptionLine[] {
  const index = lines.findIndex((existing) => existing.id === line.id);
  if (index === -1) return [...lines, line];
  const next = lines.slice();
  next[index] = line;
  return next;
}

// ---------------------------------------------------------------------------------------------
// Reading the stage

export function interviewerStatus(state: SessionState): InterviewerStatus {
  if (state.phase === "connecting") return "connecting";
  if (state.phase === "reconnecting") return "reconnecting";
  if (state.phase === "ending" || state.phase === "ended") return "ending";
  if (state.aiSpeaking) return "speaking";
  if (state.muted) return "paused";
  if (state.thinking) return "thinking";
  return "listening";
}

/** The interviewer's latest line, as it is being said. */
export function currentLine(state: SessionState): CaptionLine | null {
  for (let i = state.captions.length - 1; i >= 0; i--) {
    const line = state.captions[i]!;
    if (line.who === "ai" && line.text.trim()) return line;
  }
  return null;
}

/** Caption lines with words in them (a candidate's turn can come back empty). */
export function visibleCaptions(state: SessionState): CaptionLine[] {
  return state.captions.filter((line) => line.text.trim() !== "");
}

/** "12:05" — minutes and seconds. */
export function clock(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds));
  return `${Math.floor(safe / 60)}:${String(safe % 60).padStart(2, "0")}`;
}

/** Shown in the warning colour (frame DemoInterview: the last 2 minutes). */
export const LOW_TIME_SECONDS = 120;

/** Whole minutes at which screen readers hear how much time is left. */
export const ANNOUNCE_AT_MINUTES = [5, 1] as const;

// ---------------------------------------------------------------------------------------------
// OpenAI Realtime events

type RawEvent = Record<string, unknown>;

function str(value: unknown): string {
  return typeof value === "string" ? value : "";
}

/** One server event from the data channel, normalised; null for everything the stage ignores. */
export function readEvent(raw: unknown): TalkEvent | null {
  if (!raw || typeof raw !== "object") return null;
  const event = raw as RawEvent;
  switch (event.type) {
    case "response.output_audio_transcript.delta":
    case "response.audio_transcript.delta":
      return { type: "ai_text", id: str(event.item_id), delta: str(event.delta) };
    case "response.output_audio_transcript.done":
    case "response.audio_transcript.done":
      return { type: "ai_text_done", id: str(event.item_id), text: str(event.transcript) };
    case "output_audio_buffer.started":
      return { type: "ai_audio", playing: true };
    case "output_audio_buffer.stopped":
    case "output_audio_buffer.cleared":
      return { type: "ai_audio", playing: false };
    case "response.created":
      return { type: "thinking" };
    case "response.done":
      return { type: "response_done" };
    case "input_audio_buffer.speech_started":
      return { type: "you_started", id: str(event.item_id) };
    case "input_audio_buffer.speech_stopped":
      return { type: "you_stopped" };
    case "conversation.item.input_audio_transcription.delta":
      return { type: "you_text", id: str(event.item_id), delta: str(event.delta) };
    case "conversation.item.input_audio_transcription.completed":
      return { type: "you_text_done", id: str(event.item_id), text: str(event.transcript) };
    case "conversation.item.input_audio_transcription.failed":
      return { type: "you_text_failed", id: str(event.item_id) };
    case "response.function_call_arguments.done":
      return readToolCall(str(event.name), str(event.arguments));
    default:
      return null;
  }
}

function readToolCall(name: string, json: string): TalkEvent | null {
  let args: Record<string, unknown> = {};
  try {
    const parsed: unknown = JSON.parse(json || "{}");
    if (parsed && typeof parsed === "object") args = parsed as Record<string, unknown>;
  } catch {
    // A malformed call: the server answers it with an error; nothing to show.
  }
  if (name === "set_topic") {
    const number = args.number;
    return typeof number === "number" && Number.isInteger(number) && number >= 1
      ? { type: "topic", number }
      : null;
  }
  if (name === "show_resume_quote") {
    const text = str(args.text);
    return text ? { type: "quote", text } : null;
  }
  if (name === "end_interview") return { type: "end_requested" };
  return null;
}

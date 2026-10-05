import { describe, expect, it } from "vitest";

import {
  clock,
  currentLine,
  INITIAL_SESSION,
  interviewerStatus,
  readEvent,
  reduceSession,
  type SessionAction,
  type SessionState,
  type TalkEvent,
  visibleCaptions,
} from "@/lib/interview/session";

const STARTED: SessionAction = {
  type: "started",
  session: {
    attemptId: "a1",
    timeLeftSeconds: 1800,
    topics: [
      { number: 1, title: "Warm-up" },
      { number: 2, title: "Platform migration" },
      { number: 3, title: "Your questions" },
    ],
    topicNumber: 1,
  },
};

function run(...actions: SessionAction[]): SessionState {
  return actions.reduce(reduceSession, INITIAL_SESSION);
}

const event = (e: TalkEvent): SessionAction => ({ type: "event", event: e });
const raw = (e: Record<string, unknown>): SessionAction => {
  const parsed = readEvent(e);
  if (!parsed) throw new Error(`not read: ${JSON.stringify(e)}`);
  return event(parsed);
};

describe("captions", () => {
  it("keep the conversation in the order it was spoken, even when transcription lags", () => {
    const state = run(
      STARTED,
      { type: "connected" },
      raw({ type: "response.output_audio_transcript.delta", item_id: "ai1", delta: "Tell me " }),
      raw({ type: "response.output_audio_transcript.delta", item_id: "ai1", delta: "about it." }),
      raw({ type: "input_audio_buffer.speech_started", item_id: "you1" }),
      raw({ type: "input_audio_buffer.speech_stopped", item_id: "you1" }),
      // The interviewer answers before the candidate's words come back from transcription.
      raw({ type: "response.output_audio_transcript.delta", item_id: "ai2", delta: "Thanks." }),
      raw({
        type: "conversation.item.input_audio_transcription.completed",
        item_id: "you1",
        transcript: " I led the migration. ",
      }),
    );
    expect(visibleCaptions(state).map((line) => [line.who, line.text])).toEqual([
      ["ai", "Tell me about it."],
      ["you", "I led the migration."],
      ["ai", "Thanks."],
    ]);
    expect(currentLine(state)?.text).toBe("Thanks.");
  });

  it("drop a turn with no words and accept the beta event names", () => {
    const state = run(
      raw({ type: "input_audio_buffer.speech_started", item_id: "you1" }),
      raw({
        type: "conversation.item.input_audio_transcription.completed",
        item_id: "you1",
        transcript: "  ",
      }),
      raw({ type: "response.audio_transcript.done", item_id: "ai1", transcript: "Hello." }),
    );
    expect(state.captions.map((line) => line.id)).toEqual(["ai1"]);
    expect(state.captions[0]?.done).toBe(true);
  });
});

describe("tool calls", () => {
  const tool = (name: string, args: unknown) =>
    readEvent({
      type: "response.function_call_arguments.done",
      name,
      arguments: JSON.stringify(args),
    });

  it("are read for display only", () => {
    expect(tool("set_topic", { number: 2 })).toEqual({ type: "topic", number: 2 });
    expect(tool("set_topic", { number: 0 })).toBeNull();
    expect(tool("show_resume_quote", { text: "40 services" })).toEqual({
      type: "quote",
      text: "40 services",
    });
    expect(tool("end_interview", { reason: "completed" })).toEqual({ type: "end_requested" });
    expect(tool("something_else", {})).toBeNull();
    expect(
      readEvent({
        type: "response.function_call_arguments.done",
        name: "set_topic",
        arguments: "{",
      }),
    ).toBeNull();
  });

  it("move the topic marker (1-based) but never past the plan, and never back on a resume", () => {
    expect(run(STARTED, event({ type: "topic", number: 2 })).topicNumber).toBe(2);
    expect(run(STARTED, event({ type: "topic", number: 9 })).topicNumber).toBe(1);
    const resumed = run(STARTED, event({ type: "topic", number: 3 }), {
      ...STARTED,
      session: { ...STARTED.session, attemptId: "a2", topicNumber: 2 },
    } as SessionAction);
    expect(resumed.topicNumber).toBe(3);
  });

  it("keep the résumé quote through the answer, until the interviewer moves on", () => {
    const quoted = run(
      event({ type: "quote", text: "migrated 40 services" }),
      event({ type: "ai_text", id: "ai1", delta: "How did you decide?" }),
      event({ type: "you_started", id: "you1" }),
      event({ type: "you_text_done", id: "you1", text: "Carefully." }),
    );
    expect(quoted.quote).toBe("migrated 40 services");
    const movedOn = reduceSession(quoted, event({ type: "ai_text", id: "ai2", delta: "Next," }));
    expect(movedOn.quote).toBeNull();
  });

  it("end_interview lets the goodbye play, then a hang-up ends the session", () => {
    const ending = run(STARTED, { type: "connected" }, event({ type: "end_requested" }));
    expect(ending.phase).toBe("ending");
    expect(interviewerStatus(ending)).toBe("ending");
    expect(reduceSession(ending, { type: "connection_lost" }).phase).toBe("ended");
  });
});

describe("status", () => {
  it("follows who is talking, and says the mic is off while muted", () => {
    const live = run(STARTED, { type: "connected" });
    expect(interviewerStatus(INITIAL_SESSION)).toBe("connecting");
    expect(interviewerStatus(live)).toBe("listening");
    expect(interviewerStatus(reduceSession(live, event({ type: "thinking" })))).toBe("thinking");
    const speaking = reduceSession(live, event({ type: "ai_audio", playing: true }));
    expect(interviewerStatus(speaking)).toBe("speaking");
    const muted = reduceSession(live, { type: "mute", muted: true });
    expect(interviewerStatus(muted)).toBe("paused");
    expect(interviewerStatus(reduceSession(muted, { type: "mute", muted: false }))).toBe(
      "listening",
    );
    expect(interviewerStatus(reduceSession(live, { type: "connection_lost" }))).toBe(
      "reconnecting",
    );
  });
});

describe("time", () => {
  it("counts down while live and takes the server's number at each heartbeat", () => {
    let state = run(STARTED);
    state = reduceSession(state, { type: "tick" });
    expect(state.secondsLeft).toBe(1800); // not connected yet
    state = reduceSession(state, { type: "connected" });
    state = reduceSession(state, { type: "tick" });
    state = reduceSession(state, { type: "tick" });
    expect(state.secondsLeft).toBe(1798);
    state = reduceSession(state, { type: "heartbeat", status: "wrap_up", timeLeftSeconds: 290 });
    expect(state.secondsLeft).toBe(290);
    expect(state.wrapUp).toBe(true);
    state = reduceSession(state, { type: "heartbeat", status: "ended", timeLeftSeconds: 0 });
    expect(state.phase).toBe("ended");
    // Nothing moves an ended session but a retry.
    expect(reduceSession(state, { type: "connected" }).phase).toBe("ended");
  });

  it("shows minutes and seconds", () => {
    expect(clock(1800)).toBe("30:00");
    expect(clock(65)).toBe("1:05");
    expect(clock(-3)).toBe("0:00");
  });
});

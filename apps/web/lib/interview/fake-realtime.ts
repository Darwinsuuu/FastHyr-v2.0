// A scripted stand-in for an OpenAI Realtime call (INTV-005), for local runs with the API's
// `AI_FAKE=1`, the dev preview page and Playwright. It sends the same data-channel events a real
// call sends, word by word, and its "candidate" waits while the mic is muted. It never runs in
// production: `connectRealtime()` uses it only when asked to and the API answered with the
// fake SDP.

import type { RealtimeConnection, RealtimeHandlers } from "./realtime";
import { readEvent } from "./session";

type Step = { ai: string; topic?: number; quote?: string } | { you: string } | { end: true };

/** The scripted conversation. Generic on purpose: it isn't anyone's real interview. */
export const FAKE_SCRIPT: readonly Step[] = [
  {
    ai: "Hi, I'm the AI interviewer. Thanks for making time today. This is a relaxed conversation about your experience, and you can ask me about the role along the way. Ready to start?",
  },
  { you: "Yes, ready. Thanks for having me." },
  {
    topic: 1,
    ai: "Great. To warm up, tell me a bit about what you're working on right now.",
  },
  {
    you: "I lead a small platform team. We run the services behind payments, mostly Go and PostgreSQL.",
  },
  {
    topic: 2,
    quote: "migrated 40 services to Kubernetes",
    ai: "Your résumé says you migrated 40 services to Kubernetes. How did you decide what to move first?",
  },
  { you: "We started with the stateless services that had the best test coverage." },
  { ai: "That makes sense. Looking back, what would you do differently next time?" },
];

export interface FakeTiming {
  connectMs: number;
  wordMs: number;
  pauseMs: number;
}

const TIMING: FakeTiming = { connectMs: 300, wordMs: 70, pauseMs: 900 };

export function startFakeRealtime({
  stream,
  handlers,
  script = FAKE_SCRIPT,
  timing = TIMING,
}: {
  stream?: MediaStream;
  handlers: RealtimeHandlers;
  script?: readonly Step[];
  timing?: FakeTiming;
}): RealtimeConnection {
  let closed = false;
  let muted = false;
  const mic = stream?.getAudioTracks()[0];

  const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));
  const send = (raw: Record<string, unknown>) => {
    if (closed) return;
    const event = readEvent(raw);
    if (event) handlers.onEvent(event);
  };
  const tool = (name: string, args: Record<string, unknown>) =>
    send({
      type: "response.function_call_arguments.done",
      name,
      arguments: JSON.stringify(args),
    });

  async function say(id: string, text: string) {
    send({ type: "response.created" });
    await sleep(timing.pauseMs / 3);
    send({ type: "output_audio_buffer.started" });
    for (const word of text.split(" ")) {
      if (closed) return;
      send({ type: "response.output_audio_transcript.delta", item_id: id, delta: `${word} ` });
      await sleep(timing.wordMs);
    }
    send({ type: "response.output_audio_transcript.done", item_id: id, transcript: text });
    send({ type: "output_audio_buffer.stopped" });
    send({ type: "response.done" });
  }

  async function answer(id: string, text: string) {
    // The candidate speaks only with the mic on.
    while (muted && !closed) await sleep(200);
    send({ type: "input_audio_buffer.speech_started", item_id: id });
    await sleep(text.split(" ").length * timing.wordMs);
    send({ type: "input_audio_buffer.speech_stopped", item_id: id });
    send({
      type: "conversation.item.input_audio_transcription.completed",
      item_id: id,
      transcript: text,
    });
  }

  async function run() {
    await sleep(timing.connectMs);
    if (closed) return;
    handlers.onState("connected");
    let turn = 0;
    for (const step of script) {
      if (closed) return;
      turn += 1;
      await sleep(timing.pauseMs);
      if ("end" in step) {
        tool("end_interview", { reason: "completed" });
        await sleep(timing.pauseMs);
        if (!closed) handlers.onState("lost");
        return;
      }
      if ("you" in step) {
        await answer(`fake_you_${turn}`, step.you);
        continue;
      }
      if (step.topic) tool("set_topic", { number: step.topic });
      if (step.quote) tool("show_resume_quote", { text: step.quote });
      await say(`fake_ai_${turn}`, step.ai);
    }
  }

  void run();

  return {
    setMuted: (next) => {
      muted = next;
      if (mic) mic.enabled = !next;
    },
    close: () => {
      closed = true;
    },
  };
}

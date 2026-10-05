// @vitest-environment jsdom
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { type InterviewClient, InterviewClosedError } from "@/lib/interview/client";
import type { RealtimeHandlers } from "@/lib/interview/realtime";

import { MAX_RECONNECTS, useInterviewSession } from "./use-interview-session";

// One fake connection per connect(): the test drives its state and events.
const connections: { handlers: RealtimeHandlers; closed: boolean; muted: boolean }[] = [];

vi.mock("@/lib/interview/realtime", () => ({
  connectRealtime: vi.fn(
    async ({
      openCall,
      handlers,
    }: {
      openCall: (offer: string) => Promise<string>;
      handlers: RealtimeHandlers;
    }) => {
      await openCall("offer");
      const connection = { handlers, closed: false, muted: false };
      connections.push(connection);
      return {
        setMuted: (muted: boolean) => {
          connection.muted = muted;
        },
        close: () => {
          connection.closed = true;
        },
      };
    },
  ),
}));

vi.mock("@/lib/interview/devices", () => ({
  openStream: vi.fn(async () => ({ getAudioTracks: () => [{ enabled: true }] })),
  stopStream: vi.fn(),
}));

function fakeClient(overrides: Partial<InterviewClient> = {}) {
  let attempts = 0;
  return {
    open: vi.fn(async () => {
      attempts += 1;
      return {
        sdp: "answer",
        heartbeatSeconds: 15,
        session: {
          attemptId: `attempt-${attempts}`,
          timeLeftSeconds: 1800,
          topics: [{ number: 1, title: "Warm-up" }],
          topicNumber: 1,
        },
      };
    }),
    heartbeat: vi.fn(async () => ({ status: "active" as const, timeLeftSeconds: 1790 })),
    complete: vi.fn(async () => undefined),
    ...overrides,
  };
}

function start(client: InterviewClient, onEnded = vi.fn()) {
  const hook = renderHook(() =>
    useInterviewSession({
      client,
      video: false,
      devices: { camera: null, microphone: null },
      allowFake: false,
      onEnded,
    }),
  );
  return { ...hook, onEnded };
}

const latest = () => connections[connections.length - 1]!;

beforeEach(() => {
  vi.useFakeTimers();
  connections.length = 0;
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useInterviewSession", () => {
  it("sends the first heartbeat as soon as the connection is up, then every 15 s", async () => {
    const client = fakeClient();
    const { result } = start(client);
    await act(async () => {});
    expect(client.open).toHaveBeenCalledTimes(1);
    expect(client.heartbeat).not.toHaveBeenCalled();

    await act(async () => latest().handlers.onState("connected"));
    expect(result.current.state.phase).toBe("live");
    expect(client.heartbeat).toHaveBeenCalledWith("attempt-1", true);

    await act(async () => vi.advanceTimersByTimeAsync(15_000));
    expect(client.heartbeat).toHaveBeenCalledTimes(2);
  });

  it("reconnects after a drop with a new attempt, and gives up after repeated failures", async () => {
    const client = fakeClient();
    const { result } = start(client);
    await act(async () => {});
    await act(async () => latest().handlers.onState("connected"));

    await act(async () => latest().handlers.onState("lost"));
    expect(result.current.state.phase).toBe("reconnecting");
    expect(connections[0]!.closed).toBe(true);
    await act(async () => vi.advanceTimersByTimeAsync(1000));
    expect(client.open).toHaveBeenCalledTimes(2);
    await act(async () => latest().handlers.onState("connected"));
    expect(result.current.state.phase).toBe("live");
    expect(client.heartbeat).toHaveBeenLastCalledWith("attempt-2", true);

    // Connections that never come up.
    for (let i = 0; i <= MAX_RECONNECTS; i++) {
      await act(async () => latest().handlers.onState("lost"));
      await act(async () => vi.advanceTimersByTimeAsync(10_000));
    }
    expect(result.current.state.phase).toBe("failed");
    expect(result.current.state.failure).toBe("connect");
  });

  it("hands back to the link page when the server says the session is over", async () => {
    const client = fakeClient({
      heartbeat: vi.fn(async () => ({ status: "ended" as const, timeLeftSeconds: 0 })),
    });
    const { result, onEnded } = start(client);
    await act(async () => {});
    await act(async () => latest().handlers.onState("connected"));
    expect(result.current.state.phase).toBe("ended");
    expect(latest().closed).toBe(true);
    expect(onEnded).toHaveBeenCalledTimes(1);
  });

  it("hands back when the link closed meanwhile (time up, finished elsewhere)", async () => {
    const client = fakeClient({
      open: vi.fn(async () => {
        throw new InterviewClosedError("interview_not_open");
      }),
    });
    const { onEnded } = start(client);
    await act(async () => {});
    expect(onEnded).toHaveBeenCalledTimes(1);
  });

  it("mutes the mic and ends the interview through the API", async () => {
    const client = fakeClient();
    const { result, onEnded } = start(client);
    await act(async () => {});
    await act(async () => latest().handlers.onState("connected"));

    act(() => result.current.setMuted(true));
    expect(latest().muted).toBe(true);
    expect(result.current.state.muted).toBe(true);

    await act(async () => result.current.end());
    expect(client.complete).toHaveBeenCalledWith("attempt-1");
    expect(onEnded).toHaveBeenCalledTimes(1);
  });

  it("a hang-up after the interviewer's goodbye ends the session instead of reconnecting", async () => {
    const client = fakeClient();
    const { result, onEnded } = start(client);
    await act(async () => {});
    await act(async () => latest().handlers.onState("connected"));
    await act(async () => latest().handlers.onEvent({ type: "end_requested" }));
    expect(result.current.state.phase).toBe("ending");
    await act(async () => latest().handlers.onState("lost"));
    expect(client.open).toHaveBeenCalledTimes(1);
    expect(onEnded).toHaveBeenCalledTimes(1);
  });
});

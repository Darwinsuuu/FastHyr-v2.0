"use client";

import { useCallback, useEffect, useReducer, useRef, useState, useSyncExternalStore } from "react";

import { type InterviewClient, InterviewClosedError } from "@/lib/interview/client";
import { openStream, stopStream } from "@/lib/interview/devices";
import { connectRealtime, type RealtimeConnection } from "@/lib/interview/realtime";
import { type AttemptRecorder, CHUNK_MS, startRecorder } from "@/lib/interview/recorder";
import {
  INITIAL_SESSION,
  reduceSession,
  type SessionState,
  type TalkEvent,
} from "@/lib/interview/session";
import { RecordingUploader, type UploadProgress } from "@/lib/interview/uploader";

/** A connection that isn't up this long after the offer counts as failed. */
export const CONNECT_TIMEOUT_MS = 15_000;
/** Reconnects in a row before the stage shows "We couldn't connect you". */
export const MAX_RECONNECTS = 3;
const RECONNECT_DELAY_MS = 1000;
/** Name of the measure from "connected" to the interviewer's first audio (target p75 < 1.5 s). */
export const FIRST_UTTERANCE_MEASURE = "interview:first-utterance";

/** Recording waiting longer than this to upload shows the "connection is slow" note. */
export const BEHIND_AFTER_MS = 60_000;

export interface InterviewDevices {
  camera: string | null;
  microphone: string | null;
}

/**
 * Runs one live interview (FRONTEND.md §4 `session.ts`): opens the chosen devices, connects to
 * the Realtime call the API opens, heartbeats while connected, reconnects after a drop (the API
 * ends the old attempt and continues from the next topic), and closes everything when the
 * session ends. Each attempt is recorded from the moment its connection is up (INTV-006); the
 * chunks upload while the interview runs. `onEnded` runs once, when the link page should show
 * what's next: after the session ended and every chunk is saved.
 */
export function useInterviewSession({
  client,
  video,
  devices,
  allowFake,
  onEnded,
}: {
  client: InterviewClient;
  video: boolean;
  devices: InterviewDevices;
  allowFake: boolean;
  onEnded: () => void;
}) {
  const [state, dispatch] = useReducer(reduceSession, INITIAL_SESSION);
  const [stream, setStream] = useState<MediaStream | null>(null);

  // Each connect() takes a new generation; callbacks from an older one are ignored.
  const generation = useRef(0);
  const streamRef = useRef<MediaStream | null>(null);
  const connection = useRef<RealtimeConnection | null>(null);
  const attemptId = useRef<string | null>(null);
  const heartbeatEvery = useRef(15);
  const heartbeatTimer = useRef<ReturnType<typeof setInterval> | undefined>(undefined);
  const connectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const failures = useRef(0);
  const muted = useRef(false);
  const phase = useRef<SessionState["phase"]>(state.phase);
  const connectedAt = useRef<number | null>(null);
  const endedReported = useRef(false);
  const reconnect = useRef<() => void>(() => {});
  const [uploader] = useState(() => new RecordingUploader(client.recording));
  const recorder = useRef<{ attemptId: string; recorder: AttemptRecorder } | null>(null);
  const remote = useRef<MediaStream | null>(null);
  const recorderStopped = useRef<Promise<void>>(Promise.resolve());
  const upload = useSyncExternalStore(
    useCallback((notify: () => void) => uploader.subscribe(notify), [uploader]),
    () => uploader.current,
    () => uploader.current,
  );

  const latest = useRef({ client, video, devices, allowFake, onEnded });
  useEffect(() => {
    latest.current = { client, video, devices, allowFake, onEnded };
    phase.current = state.phase;
  });

  const stopTimers = useCallback(() => {
    clearInterval(heartbeatTimer.current);
    clearTimeout(connectTimer.current);
    clearTimeout(retryTimer.current);
  }, []);

  const dropConnection = useCallback(() => {
    connection.current?.close();
    connection.current = null;
  }, []);

  /** Starts recording the attempt whose connection just came up. */
  const startRecording = useCallback(() => {
    const id = attemptId.current;
    const media = streamRef.current;
    if (!id || !media || recorder.current?.attemptId === id) return;
    const started = startRecorder({
      stream: media,
      remote: remote.current,
      video: latest.current.video,
      onChunk: (seq, data) => uploader.add(id, seq, data),
    });
    if (!started) return;
    uploader.startAttempt(id, started.type.kind, started.type.contentType);
    recorder.current = { attemptId: id, recorder: started };
  }, [uploader]);

  /** Stops the attempt's recording; its last chunks keep uploading. */
  const stopRecording = useCallback(() => {
    const running = recorder.current;
    recorder.current = null;
    remote.current = null;
    if (!running) return;
    const stopped = running.recorder.stop().then(() => uploader.finishAttempt(running.attemptId));
    recorderStopped.current = Promise.all([recorderStopped.current, stopped]).then(() => {});
  }, [uploader]);

  /** Closes everything for good; the stage then hands back to the link page. */
  const finish = useCallback(() => {
    generation.current += 1;
    stopTimers();
    stopRecording();
    dropConnection();
    stopStream(streamRef.current);
    streamRef.current = null;
    setStream(null);
    dispatch({ type: "ended" });
  }, [dropConnection, stopRecording, stopTimers]);

  const beat = useCallback(
    async (gen: number) => {
      const id = attemptId.current;
      if (!id || gen !== generation.current) return;
      try {
        const result = await latest.current.client.heartbeat(id, true);
        if (gen !== generation.current) return;
        dispatch({
          type: "heartbeat",
          status: result.status,
          timeLeftSeconds: result.timeLeftSeconds,
        });
        if (result.status === "ended") finish();
      } catch (error) {
        if (gen !== generation.current) return;
        if (error instanceof InterviewClosedError) finish();
        // Anything else (a network blip): the next beat tries again. The server allows 60 s.
      }
    },
    [finish],
  );

  const connect = useCallback(async () => {
    const gen = ++generation.current;
    stopTimers();
    dropConnection();
    const { client: api, video: withVideo, devices: chosen, allowFake: fake } = latest.current;

    let media = streamRef.current;
    if (!media) {
      try {
        media = await openStream(withVideo, chosen);
      } catch {
        if (gen === generation.current) dispatch({ type: "failed", failure: "media" });
        return;
      }
      if (gen !== generation.current) {
        stopStream(media);
        return;
      }
      streamRef.current = media;
      setStream(media);
    }
    for (const track of media.getAudioTracks()) track.enabled = !muted.current;

    const lost = () => {
      if (gen !== generation.current) return;
      if (phase.current === "ending") {
        // The interviewer said goodbye and the server hung up.
        finish();
        return;
      }
      generation.current += 1;
      stopTimers();
      stopRecording();
      dropConnection();
      dispatch({ type: "connection_lost" });
      failures.current += 1;
      if (failures.current > MAX_RECONNECTS) {
        // Let go of the camera and mic until the candidate tries again.
        stopStream(streamRef.current);
        streamRef.current = null;
        setStream(null);
        dispatch({ type: "failed", failure: "connect" });
        return;
      }
      retryTimer.current = setTimeout(reconnect.current, RECONNECT_DELAY_MS * failures.current);
    };

    const connected = () => {
      if (gen !== generation.current) return;
      clearTimeout(connectTimer.current);
      failures.current = 0;
      connectedAt.current = performance.now();
      dispatch({ type: "connected" });
      startRecording();
      // The first beat tells the server the connection is up, so the interviewer starts.
      void beat(gen);
      clearInterval(heartbeatTimer.current);
      heartbeatTimer.current = setInterval(() => void beat(gen), heartbeatEvery.current * 1000);
    };

    const onEvent = (event: TalkEvent) => {
      if (gen !== generation.current) return;
      if (event.type === "ai_audio" && event.playing && connectedAt.current !== null) {
        measureFirstUtterance(connectedAt.current);
        connectedAt.current = null;
      }
      dispatch({ type: "event", event });
    };

    connectTimer.current = setTimeout(lost, CONNECT_TIMEOUT_MS);
    try {
      const opened = await connectRealtime({
        stream: media,
        allowFake: fake,
        handlers: {
          onEvent,
          onState: (linkState) => (linkState === "connected" ? connected() : lost()),
          onRemoteStream: (stream) => {
            if (gen !== generation.current) return;
            remote.current = stream;
            recorder.current?.recorder.addRemote(stream);
          },
        },
        openCall: async (offer) => {
          const call = await api.open(offer);
          if (gen === generation.current) {
            attemptId.current = call.session.attemptId;
            heartbeatEvery.current = call.heartbeatSeconds;
            dispatch({ type: "started", session: call.session });
          }
          return call.sdp;
        },
      });
      if (gen !== generation.current) {
        opened.close();
        return;
      }
      connection.current = opened;
      opened.setMuted(muted.current);
    } catch (error) {
      if (gen !== generation.current) return;
      if (error instanceof InterviewClosedError) {
        finish();
        return;
      }
      clearTimeout(connectTimer.current);
      lost();
    }
  }, [beat, dropConnection, finish, startRecording, stopRecording, stopTimers]);

  // Connect once on mount; close everything on unmount.
  useEffect(() => {
    reconnect.current = () => void connect();
    void connect();
    return () => {
      generation.current += 1;
      stopTimers();
      stopRecording();
      dropConnection();
      stopStream(streamRef.current);
      streamRef.current = null;
    };
  }, [connect, dropConnection, stopRecording, stopTimers]);

  // Uploads stop only when the page goes; until then they retry.
  useEffect(() => {
    uploader.open();
    return () => uploader.dispose();
  }, [uploader]);

  // The countdown between heartbeats.
  const ticking = state.phase === "live" || state.phase === "ending";
  useEffect(() => {
    if (!ticking) return;
    const timer = setInterval(() => dispatch({ type: "tick" }), 1000);
    return () => clearInterval(timer);
  }, [ticking]);

  // Leaving or reloading mid-interview, or while the recording uploads, asks first.
  const inCall = ["connecting", "live", "reconnecting", "ending"].includes(state.phase);
  const saving = upload.waiting > 0;
  useEffect(() => {
    if (!inCall && !saving) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [inCall, saving]);

  // The link page takes over once the session ended and the recording is saved.
  useEffect(() => {
    if (state.phase !== "ended" || endedReported.current) return;
    endedReported.current = true;
    void recorderStopped.current.then(() => uploader.idle()).then(() => latest.current.onEnded());
  }, [state.phase, uploader]);

  const setMuted = useCallback((next: boolean) => {
    muted.current = next;
    for (const track of streamRef.current?.getAudioTracks() ?? []) track.enabled = !next;
    connection.current?.setMuted(next);
    dispatch({ type: "mute", muted: next });
  }, []);

  /** "End interview", after the confirm: the server completes it and hangs up. */
  const end = useCallback(async () => {
    try {
      await latest.current.client.complete(attemptId.current);
    } catch (error) {
      if (!(error instanceof InterviewClosedError)) throw error;
    }
    finish();
  }, [finish]);

  const retry = useCallback(() => {
    failures.current = 0;
    dispatch({ type: "retry" });
    void connect();
  }, [connect]);

  return { state, stream, setMuted, end, retry, upload: uploadStatus(upload) };
}

function measureFirstUtterance(start: number) {
  try {
    performance.measure(FIRST_UTTERANCE_MEASURE, { start, end: performance.now() });
  } catch {
    // Older browsers without measure options: the number is only for checking the target.
  }
}

export interface UploadStatus {
  /** Chunks still waiting to be saved. */
  waiting: number;
  /** Share of the recording saved so far, 0–100. */
  percent: number;
  /** More than a minute of recording is waiting: the connection can't keep up. */
  behind: boolean;
}

export function uploadStatus(progress: UploadProgress): UploadStatus {
  const percent =
    progress.totalBytes === 0 ? 100 : Math.floor((progress.savedBytes / progress.totalBytes) * 100);
  return {
    waiting: progress.waiting,
    percent: progress.waiting > 0 ? Math.min(percent, 99) : 100,
    behind: progress.waiting * CHUNK_MS > BEHIND_AFTER_MS,
  };
}

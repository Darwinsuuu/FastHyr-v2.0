// The live interview's calls to the API (INTV-004's contract): open a call with the browser's
// offer, heartbeat every `heartbeat_seconds` (the first as soon as the connection is up), and
// end it. Behind an interface so the dev preview and tests can run the stage without the API.

import { api, ApiError, unwrap } from "@/lib/api/client";

import type { SessionStart } from "./session";
import { RecordingClosedError, RecordingRejectedError, type RecordingApi } from "./uploader";

export interface OpenedCall {
  session: SessionStart;
  /** OpenAI's SDP answer. */
  sdp: string;
  heartbeatSeconds: number;
}

export interface HeartbeatResult {
  status: "active" | "wrap_up" | "ended";
  timeLeftSeconds: number;
}

export interface InterviewClient {
  open: (offer: string) => Promise<OpenedCall>;
  heartbeat: (attemptId: string, connected: boolean) => Promise<HeartbeatResult>;
  complete: (attemptId: string | null) => Promise<void>;
  /** Where the recording's chunks go (INTV-006). */
  recording: RecordingApi;
}

/**
 * The interview can't go on from here: it finished, expired or closed, or the server gave up on
 * connecting (`interview_technical_issue`). The link page shows what's next.
 */
export class InterviewClosedError extends Error {
  constructor(readonly code: string | null) {
    super(code ?? "interview_closed");
    this.name = "InterviewClosedError";
  }
}

const CLOSED_CODES = new Set([
  "interview_not_open",
  "interview_technical_issue",
  "interview_consent_required",
  "interview_not_found",
  "interview_attempt_not_found",
]);

/** Turns the API's "this interview is over or gone" answers into `InterviewClosedError`. */
function closedOr(error: unknown): unknown {
  if (error instanceof ApiError && (error.status === 404 || CLOSED_CODES.has(error.code ?? ""))) {
    return new InterviewClosedError(error.code ?? null);
  }
  return error;
}

const RECORDING_CLOSED_CODES = new Set([
  "recording_finalized",
  "recording_type_mismatch",
  "interview_not_open",
  "interview_not_found",
  "interview_attempt_not_found",
]);

/** Sorts the API's answers for the uploader: stop this attempt, skip this chunk, or retry. */
function recordingError(error: unknown): unknown {
  if (!(error instanceof ApiError)) return error;
  if (error.status === 404 || RECORDING_CLOSED_CODES.has(error.code ?? "")) {
    return new RecordingClosedError(error.code ?? null);
  }
  if (error.code === "recording_chunk_too_large") return new RecordingRejectedError(error.status);
  return error;
}

export function apiInterviewClient(token: string): InterviewClient {
  const path = { token };
  return {
    async open(offer) {
      try {
        const session = unwrap(
          await api.POST("/v1/candidate/interviews/{token}/session", {
            params: { path },
            body: { sdp: offer },
          }),
        );
        return {
          sdp: session.sdp,
          heartbeatSeconds: session.heartbeat_seconds,
          session: {
            attemptId: session.attempt_id,
            timeLeftSeconds: session.time_left_seconds,
            topics: session.topics,
            topicNumber: session.topic_number,
          },
        };
      } catch (error) {
        throw closedOr(error);
      }
    },
    async heartbeat(attemptId, connected) {
      try {
        const beat = unwrap(
          await api.POST("/v1/candidate/interviews/{token}/heartbeat", {
            params: { path },
            body: { attempt_id: attemptId, connected },
          }),
        );
        return { status: beat.status, timeLeftSeconds: beat.time_left_seconds };
      } catch (error) {
        throw closedOr(error);
      }
    },
    async complete(attemptId) {
      try {
        unwrap(
          await api.POST("/v1/candidate/interviews/{token}/complete", {
            params: { path },
            body: { attempt_id: attemptId },
          }),
        );
      } catch (error) {
        throw closedOr(error);
      }
    },
    recording: {
      async chunkUrls(attemptId, kind, fromSeq, count) {
        try {
          const batch = unwrap(
            await api.POST("/v1/candidate/interviews/{token}/chunk-urls", {
              params: { path },
              body: { attempt_id: attemptId, type: kind, from_seq: fromSeq, count },
            }),
          );
          return batch.urls;
        } catch (error) {
          throw recordingError(error);
        }
      },
      async register(attemptId, seq, last) {
        try {
          unwrap(
            await api.POST("/v1/candidate/interviews/{token}/chunks", {
              params: { path },
              body: { attempt_id: attemptId, seq, last },
            }),
          );
        } catch (error) {
          throw recordingError(error);
        }
      },
    },
  };
}

// Uploading the interview's recording chunks (INTV-006, MEDIA.md §3, STORAGE.md). One uploader
// serves the whole interview: chunks from every attempt wait in one queue and go up in order,
// each to its own signed URL, then are registered with the API. Failures retry with backoff for
// as long as the page is open; nothing is dropped while it waits.

import type { RecordingKind } from "./recorder";

export interface RecordingApi {
  /** Signed upload URLs for chunks `fromSeq` … `fromSeq + count - 1`. */
  chunkUrls: (
    attemptId: string,
    kind: RecordingKind,
    fromSeq: number,
    count: number,
  ) => Promise<{ seq: number; url: string }[]>;
  register: (attemptId: string, seq: number, last: boolean) => Promise<void>;
  /** Uploads a chunk to its URL; by default a PUT to the signed Storage URL. */
  put?: (url: string, data: Blob, contentType: string) => Promise<void>;
}

/** Why the API won't take more chunks for an attempt (the recording is already saved, or the
 * interview is gone). The uploader drops that attempt's chunks. */
export class RecordingClosedError extends Error {
  constructor(readonly code: string | null) {
    super(code ?? "recording_closed");
    this.name = "RecordingClosedError";
  }
}

/** A failure that retrying the same request won't fix (Storage or the API refused the chunk).
 * The uploader tries such a chunk a few times, then moves on to the next one. */
export class RecordingRejectedError extends Error {
  constructor(readonly status: number) {
    super(`recording chunk refused (${status})`);
    this.name = "RecordingRejectedError";
  }
}

export interface UploadProgress {
  /** Bytes recorded so far, and how many of them are saved. */
  totalBytes: number;
  savedBytes: number;
  /** Chunks still waiting to be saved. */
  waiting: number;
}

/** URLs asked for at a time, and when to ask for more. */
export const URL_BATCH = 24;
export const URL_REFILL_AT = 12;
const RETRY_FIRST_MS = 1000;
const RETRY_MAX_MS = 30_000;
const REJECTED_TRIES = 3;

type Task =
  | { type: "chunk"; attemptId: string; seq: number; data: Blob }
  | { type: "last"; attemptId: string };

interface Attempt {
  kind: RecordingKind;
  contentType: string;
  urls: Map<number, string>;
  /** The next chunk number URLs haven't been asked for yet. */
  nextUrlSeq: number;
  lastSeq: number | null;
  closed: boolean;
  fetching: Promise<void> | null;
}

export class RecordingUploader {
  private readonly attempts = new Map<string, Attempt>();
  private readonly queue: Task[] = [];
  private running = false;
  private disposed = false;
  private progress: UploadProgress = { totalBytes: 0, savedBytes: 0, waiting: 0 };
  private readonly listeners = new Set<(progress: UploadProgress) => void>();
  private readonly idleWaiters: (() => void)[] = [];

  constructor(
    private readonly api: RecordingApi,
    private readonly options: {
      send?: typeof fetch;
      sleep?: (ms: number) => Promise<void>;
    } = {},
  ) {}

  startAttempt(attemptId: string, kind: RecordingKind, contentType: string) {
    if (this.attempts.has(attemptId)) return;
    this.attempts.set(attemptId, {
      kind,
      contentType,
      urls: new Map(),
      nextUrlSeq: 0,
      lastSeq: null,
      closed: false,
      fetching: null,
    });
  }

  add(attemptId: string, seq: number, data: Blob) {
    if (!this.attempts.has(attemptId) || this.disposed) return;
    this.queue.push({ type: "chunk", attemptId, seq, data });
    this.update({
      totalBytes: this.progress.totalBytes + data.size,
      waiting: this.progress.waiting + 1,
    });
    this.pump();
  }

  /** The attempt's recorder stopped: once its chunks are saved, tell the API nothing follows. */
  finishAttempt(attemptId: string) {
    if (!this.attempts.has(attemptId) || this.disposed) return;
    this.queue.push({ type: "last", attemptId });
    this.pump();
  }

  get current(): UploadProgress {
    return this.progress;
  }

  subscribe(listener: (progress: UploadProgress) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /** Resolves once everything handed over so far is saved (or given up). */
  idle(): Promise<void> {
    if (!this.running && this.queue.length === 0) return Promise.resolve();
    return new Promise((resolve) => this.idleWaiters.push(resolve));
  }

  /** Takes chunks again after `dispose()` (React runs effects twice in development). */
  open() {
    this.disposed = false;
  }

  dispose() {
    this.disposed = true;
    this.queue.length = 0;
    this.listeners.clear();
    this.flushIdle();
  }

  private update(next: Partial<UploadProgress>) {
    this.progress = { ...this.progress, ...next };
    for (const listener of this.listeners) listener(this.progress);
  }

  private flushIdle() {
    for (const resolve of this.idleWaiters.splice(0)) resolve();
  }

  private pump() {
    if (this.running) return;
    this.running = true;
    void (async () => {
      while (this.queue.length > 0 && !this.disposed) {
        const task = this.queue[0]!;
        await this.run(task);
        this.queue.shift();
      }
      this.running = false;
      this.flushIdle();
    })();
  }

  private async run(task: Task) {
    const attempt = this.attempts.get(task.attemptId);
    if (!attempt) return;
    if (task.type === "last") {
      if (attempt.lastSeq !== null && !attempt.closed) {
        const seq = attempt.lastSeq;
        await this.retrying(attempt, () => this.api.register(task.attemptId, seq, true));
      }
      return;
    }
    let saved = false;
    if (!attempt.closed) {
      saved = await this.retrying(attempt, async () => {
        const url = await this.urlFor(task.attemptId, attempt, task.seq);
        await this.put(url, task.data, attempt.contentType);
        await this.api.register(task.attemptId, task.seq, false);
      });
    }
    if (saved) attempt.lastSeq = Math.max(attempt.lastSeq ?? -1, task.seq);
    this.update({
      savedBytes: this.progress.savedBytes + task.data.size,
      waiting: Math.max(0, this.progress.waiting - 1),
    });
  }

  /** Runs `step` until it works, waiting longer after each failure. False if the attempt
   * closed, the step was refused a few times, or the uploader was disposed. */
  private async retrying(attempt: Attempt, step: () => Promise<void>): Promise<boolean> {
    let wait = RETRY_FIRST_MS;
    let rejected = 0;
    while (!this.disposed && !attempt.closed) {
      try {
        await step();
        return true;
      } catch (error) {
        if (error instanceof RecordingClosedError) {
          attempt.closed = true;
          return false;
        }
        if (error instanceof RecordingRejectedError && ++rejected >= REJECTED_TRIES) return false;
        await (this.options.sleep ?? defaultSleep)(wait);
        wait = Math.min(wait * 2, RETRY_MAX_MS);
      }
    }
    return false;
  }

  private async urlFor(attemptId: string, attempt: Attempt, seq: number): Promise<string> {
    if (!attempt.urls.has(seq)) {
      attempt.nextUrlSeq = Math.max(attempt.nextUrlSeq, seq);
      await this.fetchUrls(attemptId, attempt);
    } else if (attempt.nextUrlSeq - seq <= URL_REFILL_AT) {
      // Ask for the next batch in the background, before it's needed.
      void this.fetchUrls(attemptId, attempt).catch(() => {});
    }
    const url = attempt.urls.get(seq);
    if (!url) throw new Error("no upload URL");
    return url;
  }

  private fetchUrls(attemptId: string, attempt: Attempt): Promise<void> {
    attempt.fetching ??= (async () => {
      try {
        const from = attempt.nextUrlSeq;
        const urls = await this.api.chunkUrls(attemptId, attempt.kind, from, URL_BATCH);
        for (const { seq, url } of urls) attempt.urls.set(seq, url);
        attempt.nextUrlSeq = Math.max(attempt.nextUrlSeq, from + URL_BATCH);
      } finally {
        attempt.fetching = null;
      }
    })();
    return attempt.fetching;
  }

  private async put(url: string, data: Blob, contentType: string) {
    if (this.api.put) return this.api.put(url, data, contentType);
    const response = await (this.options.send ?? fetch)(url, {
      method: "PUT",
      body: data,
      headers: { "Content-Type": contentType },
    });
    if (response.ok || (await isDuplicate(response))) return;
    if (response.status >= 400 && response.status < 500 && ![408, 429].includes(response.status)) {
      throw new RecordingRejectedError(response.status);
    }
    throw new Error(`upload failed (${response.status})`);
  }
}

/** Storage answers a second upload to the same signed URL with "Duplicate": the first one
 * worked (its answer was lost), so the chunk is there. */
async function isDuplicate(response: Response): Promise<boolean> {
  if (response.status === 409) return true;
  if (response.status !== 400) return false;
  try {
    const body = (await response.json()) as { statusCode?: string; error?: string };
    return body.statusCode === "409" || body.error === "Duplicate";
  } catch {
    return false;
  }
}

function defaultSleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

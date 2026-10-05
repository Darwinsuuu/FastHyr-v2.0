import { describe, expect, it, vi } from "vitest";

import { chooseRecordingType } from "./recorder";
import { RecordingClosedError, type RecordingApi, RecordingUploader, URL_BATCH } from "./uploader";

function fakeApi(overrides: Partial<RecordingApi> = {}) {
  const registered: [string, number, boolean][] = [];
  const chunkUrls = vi.fn(async (attemptId: string, kind: string, fromSeq: number, count: number) =>
    Array.from({ length: count }, (_, index) => ({
      seq: fromSeq + index,
      url: `https://storage.test/${attemptId}/${fromSeq + index}.${kind}`,
    })),
  );
  const register = vi.fn(async (attemptId: string, seq: number, last: boolean) => {
    registered.push([attemptId, seq, last]);
  });
  const api: RecordingApi = { chunkUrls, register, ...overrides };
  return { api, chunkUrls, registered };
}

const ok = () => new Response(null, { status: 200 });
const chunk = (bytes = 10) => new Blob([new Uint8Array(bytes)]);
const noSleep = async () => {};

describe("RecordingUploader", () => {
  it("uploads chunks in order, registers each, then marks the attempt's last one", async () => {
    const { api, chunkUrls, registered } = fakeApi();
    const send = vi.fn<typeof fetch>(async () => ok());
    const uploader = new RecordingUploader(api, { send, sleep: noSleep });
    uploader.startAttempt("a1", "webm", "video/webm");
    uploader.add("a1", 0, chunk(10));
    uploader.add("a1", 1, chunk(30));
    uploader.finishAttempt("a1");
    expect(uploader.current).toMatchObject({ totalBytes: 40, waiting: 2 });

    await uploader.idle();

    expect(send.mock.calls.map(([url]) => url)).toEqual([
      "https://storage.test/a1/0.webm",
      "https://storage.test/a1/1.webm",
    ]);
    expect(send.mock.calls[0]?.[1]).toMatchObject({
      method: "PUT",
      headers: { "Content-Type": "video/webm" },
    });
    expect(registered).toEqual([
      ["a1", 0, false],
      ["a1", 1, false],
      ["a1", 1, true],
    ]);
    expect(uploader.current).toEqual({ totalBytes: 40, savedBytes: 40, waiting: 0 });
    // One batch of URLs covers the start of the recording.
    expect(chunkUrls).toHaveBeenCalledWith("a1", "webm", 0, URL_BATCH);
  });

  it("retries a failed upload and counts Storage's duplicate answer as uploaded", async () => {
    const { api, registered } = fakeApi();
    const send = vi
      .fn<typeof fetch>()
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(new Response(null, { status: 503 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ statusCode: "409", error: "Duplicate" }), { status: 400 }),
      );
    const sleep = vi.fn<(ms: number) => Promise<void>>(async () => {});
    const uploader = new RecordingUploader(api, { send, sleep });
    uploader.startAttempt("a1", "mp4", "video/mp4");
    uploader.add("a1", 0, chunk());

    await uploader.idle();

    expect(send).toHaveBeenCalledTimes(3);
    expect(sleep.mock.calls.map(([ms]) => ms)).toEqual([1000, 2000]);
    expect(registered).toEqual([["a1", 0, false]]);
  });

  it("asks for more URLs before the batch runs out", async () => {
    const { api, chunkUrls } = fakeApi();
    const uploader = new RecordingUploader(api, { send: async () => ok(), sleep: noSleep });
    uploader.startAttempt("a1", "webm", "video/webm");
    for (let seq = 0; seq < 14; seq += 1) uploader.add("a1", seq, chunk());

    await uploader.idle();

    expect(chunkUrls.mock.calls.map((call) => call[2])).toEqual([0, URL_BATCH]);
  });

  it("drops an attempt's chunks once the API closes it, and goes on with the next attempt", async () => {
    const { api, registered } = fakeApi({
      chunkUrls: vi.fn(async (attemptId: string, kind: string, fromSeq: number) => {
        if (attemptId === "a1") throw new RecordingClosedError("recording_finalized");
        return [{ seq: fromSeq, url: `https://storage.test/${attemptId}/${fromSeq}.${kind}` }];
      }),
    });
    const send = vi.fn<typeof fetch>(async () => ok());
    const uploader = new RecordingUploader(api, { send, sleep: noSleep });
    uploader.startAttempt("a1", "webm", "video/webm");
    uploader.startAttempt("a2", "webm", "video/webm");
    uploader.add("a1", 0, chunk());
    uploader.add("a1", 1, chunk());
    uploader.add("a2", 0, chunk());
    uploader.finishAttempt("a1");

    await uploader.idle();

    expect(registered).toEqual([["a2", 0, false]]);
    expect(uploader.current.waiting).toBe(0);
  });
});

describe("chooseRecordingType", () => {
  it("prefers WebM and falls back to MP4 (Safari), audio only for voice interviews", () => {
    expect(chooseRecordingType(true, () => true)).toEqual({
      mimeType: "video/webm;codecs=vp9,opus",
      kind: "webm",
      contentType: "video/webm",
    });
    const safari = (type: string) => type.startsWith("video/mp4") || type.startsWith("audio/mp4");
    expect(chooseRecordingType(true, safari)).toMatchObject({
      kind: "mp4",
      contentType: "video/mp4",
    });
    expect(chooseRecordingType(false, safari)).toMatchObject({
      kind: "mp4",
      contentType: "audio/mp4",
    });
    expect(chooseRecordingType(true, () => false)).toBeNull();
  });
});

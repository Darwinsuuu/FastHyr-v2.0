// Recording one attempt of the live interview (INTV-006, MEDIA.md §3): the candidate's camera
// (video interviews) and one audio track mixing their microphone with the interviewer's voice,
// recorded by MediaRecorder in short chunks so a closed tab loses only the chunk it was
// recording. Each chunk goes to the uploader as soon as it exists.

export type RecordingKind = "webm" | "mp4";

export interface RecordingType {
  mimeType: string;
  kind: RecordingKind;
  /** The type each chunk is uploaded as (the bucket checks it). */
  contentType: string;
}

/** Chunk length. 5 s keeps a closed tab's loss under 10 s even with one chunk still uploading. */
export const CHUNK_MS = 5000;
export const VIDEO_BITS_PER_SECOND = 1_000_000;
export const AUDIO_BITS_PER_SECOND = 64_000;

const VIDEO_TYPES = [
  "video/webm;codecs=vp9,opus",
  "video/webm;codecs=vp8,opus",
  "video/webm",
  // Safari.
  "video/mp4;codecs=avc1,mp4a.40.2",
  "video/mp4",
];
const AUDIO_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4;codecs=mp4a.40.2",
  "audio/mp4",
];

/** The first container and codecs this browser can record, or null when it can't record. */
export function chooseRecordingType(
  video: boolean,
  isTypeSupported: (type: string) => boolean = (type) =>
    typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(type),
): RecordingType | null {
  for (const mimeType of video ? VIDEO_TYPES : AUDIO_TYPES) {
    let supported = false;
    try {
      supported = isTypeSupported(mimeType);
    } catch {
      supported = false;
    }
    if (!supported) continue;
    const kind: RecordingKind = mimeType.includes("mp4") ? "mp4" : "webm";
    return { mimeType, kind, contentType: `${video ? "video" : "audio"}/${kind}` };
  }
  return null;
}

// One audio context for every attempt, started inside the Start tap (`unlockAudio`): iOS
// Safari keeps a context created later suspended, and a suspended mix records silence.
let sharedContext: AudioContext | null = null;

/** Starts the audio context the recording mixes in. Call it from a tap or click handler. */
export function unlockAudio() {
  if (typeof AudioContext === "undefined") return;
  try {
    sharedContext ??= new AudioContext();
    void sharedContext.resume().catch(() => {});
  } catch {
    sharedContext = null;
  }
}

export interface AttemptRecorder {
  type: RecordingType;
  /** Adds the interviewer's audio to the mix (it can arrive after recording started). */
  addRemote: (stream: MediaStream) => void;
  /** Stops recording; resolves after the last chunk was handed over. */
  stop: () => Promise<void>;
}

/**
 * Starts recording an attempt from `stream` (camera and microphone) plus the interviewer's
 * audio. `onChunk` gets each chunk in order, numbered from 0. Returns null when the browser
 * can't record; the interview goes on without a recording.
 */
export function startRecorder({
  stream,
  remote,
  video,
  onChunk,
}: {
  stream: MediaStream;
  remote: MediaStream | null;
  video: boolean;
  onChunk: (seq: number, data: Blob) => void;
}): AttemptRecorder | null {
  const type = chooseRecordingType(video);
  if (!type || typeof AudioContext === "undefined") return null;

  // One audio track for both sides: MediaRecorder records one audio track at most.
  const context =
    sharedContext && sharedContext.state !== "closed" ? sharedContext : new AudioContext();
  const owned = context !== sharedContext;
  void context.resume().catch(() => {});
  const mix = context.createMediaStreamDestination();
  const sources: MediaStreamAudioSourceNode[] = [];
  const addAudio = (from: MediaStream) => {
    if (from.getAudioTracks().length === 0) return;
    const source = context.createMediaStreamSource(from);
    source.connect(mix);
    sources.push(source);
  };
  addAudio(stream);
  if (remote) addAudio(remote);

  const tracks = [...mix.stream.getAudioTracks()];
  const camera = video ? stream.getVideoTracks()[0] : undefined;
  if (camera) tracks.unshift(camera);

  let recorder: MediaRecorder;
  try {
    recorder = new MediaRecorder(new MediaStream(tracks), {
      mimeType: type.mimeType,
      audioBitsPerSecond: AUDIO_BITS_PER_SECOND,
      ...(camera ? { videoBitsPerSecond: VIDEO_BITS_PER_SECOND } : {}),
    });
  } catch {
    for (const source of sources) source.disconnect();
    if (owned) void context.close().catch(() => {});
    return null;
  }

  let seq = 0;
  recorder.ondataavailable = (event) => {
    if (event.data.size > 0) onChunk(seq++, event.data);
  };
  const stopped = new Promise<void>((resolve) => {
    recorder.onstop = () => resolve();
    recorder.onerror = () => resolve();
  });
  recorder.start(CHUNK_MS);

  let stopping: Promise<void> | null = null;
  return {
    type,
    addRemote: (from) => {
      if (!stopping) addAudio(from);
    },
    stop: () => {
      stopping ??= (async () => {
        if (recorder.state !== "inactive") recorder.stop();
        // The final chunk arrives before "stop"; don't wait forever on a broken recorder.
        await Promise.race([stopped, new Promise((resolve) => setTimeout(resolve, 2000))]);
        for (const source of sources) source.disconnect();
        mix.disconnect();
        if (owned) await context.close().catch(() => {});
      })();
      return stopping;
    },
  };
}

// The device check before an interview (INTV-003, MEDIA.md §1, FR-INTV-03): camera and
// microphone permission, device pickers, the microphone level meter and read-aloud check, the
// wave and face-in-frame checks on the camera preview, and fix steps for blocked permissions.
// Everything runs in the browser: no frame or sound leaves the device during the check. The
// pure parts (classification, detectors, judgements) are separate so they can be unit tested.

export type DeviceKind = "camera" | "microphone";

// ---------------------------------------------------------------------------------------------
// Permission problems and browser help

/** Why the browser didn't give us the camera or microphone. */
export type MediaProblem = "denied" | "not_found" | "in_use" | "unsupported" | "failed";

/** Reads a `getUserMedia` failure. */
export function mediaProblemOf(error: unknown): MediaProblem {
  const name =
    typeof error === "object" && error !== null && "name" in error
      ? String((error as { name: unknown }).name)
      : "";
  switch (name) {
    case "NotAllowedError":
    case "PermissionDeniedError":
    case "SecurityError":
      return "denied";
    case "NotFoundError":
    case "DevicesNotFoundError":
    case "OverconstrainedError":
      return "not_found";
    case "NotReadableError":
    case "TrackStartError":
    case "AbortError":
      return "in_use";
    case "Unsupported":
      return "unsupported";
    default:
      return "failed";
  }
}

/** Which fix steps to show for a blocked permission. */
export type BrowserKind =
  "chrome" | "edge" | "firefox" | "safari" | "ios" | "iosApp" | "android" | "inApp" | "other";

// In-app browsers (LinkedIn, Facebook, Instagram, LINE…) often can't use the camera at all.
const IN_APP = /\b(FBAN|FBAV|FB_IAB|Instagram|LinkedInApp|Line\/|MicroMessenger|GSA\/)/;

export function browserOf(userAgent: string, maxTouchPoints = 0): BrowserKind {
  if (IN_APP.test(userAgent)) return "inApp";
  // iPadOS reports itself as a Mac; touch gives it away.
  const ios =
    /iPhone|iPad|iPod/.test(userAgent) || (/Macintosh/.test(userAgent) && maxTouchPoints > 1);
  if (ios) return /CriOS|FxiOS|EdgiOS|OPiOS/.test(userAgent) ? "iosApp" : "ios";
  if (/Android/.test(userAgent)) return "android";
  if (/Edg\//.test(userAgent)) return "edge";
  if (/Firefox\//.test(userAgent)) return "firefox";
  if (/Chrome\/|Chromium\//.test(userAgent)) return "chrome";
  if (/Safari\//.test(userAgent)) return "safari";
  return "other";
}

/** Whether this page can ask for the camera and microphone at all. */
export function mediaSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    window.isSecureContext &&
    typeof navigator.mediaDevices?.getUserMedia === "function"
  );
}

// ---------------------------------------------------------------------------------------------
// Streams, pickers and the remembered choice

const STORAGE_KEYS: Record<DeviceKind, string> = {
  camera: "fh_interview_camera",
  microphone: "fh_interview_microphone",
};

/** The device the candidate picked last time, if the browser lets us read it. */
export function rememberedDevice(kind: DeviceKind): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEYS[kind]);
  } catch {
    return null;
  }
}

export function rememberDevice(kind: DeviceKind, deviceId: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEYS[kind], deviceId);
  } catch {
    // Private mode or storage blocked: the default device is fine.
  }
}

/** Constraints for one kind of device: the chosen one if any, otherwise the default. */
export function constraintsFor(kind: DeviceKind, deviceId: string | null): MediaTrackConstraints {
  const device = deviceId ? { deviceId: { ideal: deviceId } } : {};
  return kind === "camera"
    ? { ...device, facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } }
    : { ...device, echoCancellation: true, noiseSuppression: true, autoGainControl: true };
}

/**
 * Opens the camera (when `video`) and microphone. A remembered device that's gone falls back to
 * the default. Throws what `getUserMedia` throws; read it with `mediaProblemOf()`.
 */
export async function openStream(
  video: boolean,
  devices: { camera?: string | null; microphone?: string | null } = {},
): Promise<MediaStream> {
  if (!mediaSupported()) {
    throw Object.assign(new Error("Media devices are not available"), { name: "Unsupported" });
  }
  return navigator.mediaDevices.getUserMedia({
    audio: constraintsFor("microphone", devices.microphone ?? null),
    video: video ? constraintsFor("camera", devices.camera ?? null) : false,
  });
}

/** Opens just one kind of device, to switch to another camera or microphone. */
export async function openDevice(kind: DeviceKind, deviceId: string): Promise<MediaStreamTrack> {
  const stream = await navigator.mediaDevices.getUserMedia(
    kind === "camera"
      ? { video: constraintsFor("camera", deviceId) }
      : { audio: constraintsFor("microphone", deviceId) },
  );
  const [track] = kind === "camera" ? stream.getVideoTracks() : stream.getAudioTracks();
  if (!track) throw Object.assign(new Error("No track"), { name: "NotFoundError" });
  return track;
}

export function stopStream(stream: MediaStream | null | undefined): void {
  stream?.getTracks().forEach((track) => track.stop());
}

export interface DeviceOption {
  deviceId: string;
  label: string;
}

type DeviceInfo = Pick<MediaDeviceInfo, "deviceId" | "groupId" | "kind" | "label">;

/** The cameras and microphones the browser lists (labels appear once permission is given). */
export async function listDevices(): Promise<DeviceInfo[]> {
  return navigator.mediaDevices.enumerateDevices();
}

const KINDS: Record<DeviceKind, MediaDeviceKind> = {
  camera: "videoinput",
  microphone: "audioinput",
};

/** One option per real device: drops the "default"/"communications" aliases Chrome adds. */
export function deviceOptions(all: DeviceInfo[], kind: DeviceKind): DeviceOption[] {
  return all
    .filter(
      (device) =>
        device.kind === KINDS[kind] &&
        device.deviceId !== "" &&
        device.deviceId !== "default" &&
        device.deviceId !== "communications",
    )
    .map((device) => ({ deviceId: device.deviceId, label: device.label }));
}

/**
 * A picker's options and the one in use. Chrome reports its "default" alias for the device in
 * use, which shares a `groupId` with the real device; when no real device matches, the alias
 * itself is listed so the picker never shows a blank choice.
 */
export function pickerFor(
  all: DeviceInfo[],
  kind: DeviceKind,
  inUse: string | null,
): { options: DeviceOption[]; selected: string | null } {
  const options = deviceOptions(all, kind);
  if (!inUse || options.some((option) => option.deviceId === inUse)) {
    return { options, selected: inUse };
  }
  const alias = all.find((device) => device.kind === KINDS[kind] && device.deviceId === inUse);
  if (!alias) return { options, selected: null };
  const real = all.find(
    (device) =>
      device.kind === KINDS[kind] &&
      device.groupId === alias.groupId &&
      options.some((option) => option.deviceId === device.deviceId),
  );
  if (real) return { options, selected: real.deviceId };
  return {
    options: [{ deviceId: alias.deviceId, label: alias.label }, ...options],
    selected: inUse,
  };
}

/** The device a track is using, to remember it and show it in the picker. */
export function deviceIdOf(track: MediaStreamTrack | undefined): string | null {
  return track?.getSettings().deviceId ?? null;
}

// ---------------------------------------------------------------------------------------------
// Microphone: level meter and the read-aloud check

/** Root mean square of one block of samples (−1…1). */
export function rms(samples: Float32Array): number {
  if (samples.length === 0) return 0;
  let sum = 0;
  for (const sample of samples) sum += sample * sample;
  return Math.sqrt(sum / samples.length);
}

/** The meter's 0…1 height for a level: −60 dBFS (silence) to −10 dBFS (loud speech). */
export function meterLevel(level: number): number {
  if (level <= 0) return 0;
  const db = 20 * Math.log10(level);
  return Math.min(1, Math.max(0, (db + 60) / 50));
}

/** Speech at a normal volume sits well above this (−38 dBFS); room noise sits below it. */
export const SPEECH_LEVEL = 0.0126;
/** How much speech the read-aloud check needs (MEDIA.md §1). */
export const SPEECH_MS = 2000;
/** After this long without enough speech, the check asks the candidate to fix their mic. */
export const LISTEN_TIMEOUT_MS = 20000;

/** Adds up speech-level time while the candidate reads the sentence. */
export class SpeechCheck {
  heardMs = 0;
  listenedMs = 0;

  constructor(
    private readonly requiredMs = SPEECH_MS,
    private readonly timeoutMs = LISTEN_TIMEOUT_MS,
  ) {}

  /** One meter reading over `elapsedMs`. */
  add(level: number, elapsedMs: number): "listening" | "heard" | "too_quiet" {
    this.listenedMs += elapsedMs;
    if (level >= SPEECH_LEVEL) this.heardMs += elapsedMs;
    if (this.heardMs >= this.requiredMs) return "heard";
    if (this.listenedMs >= this.timeoutMs) return "too_quiet";
    return "listening";
  }
}

/** Reads the microphone's level through Web Audio. Create it inside a tap (iOS Safari). */
export class LevelMeter {
  private readonly analyser: AnalyserNode;
  private readonly samples: Float32Array<ArrayBuffer>;
  private source: MediaStreamAudioSourceNode | null = null;

  constructor(private readonly context: AudioContext) {
    this.analyser = context.createAnalyser();
    this.analyser.fftSize = 1024;
    this.samples = new Float32Array(this.analyser.fftSize);
  }

  static create(): LevelMeter | null {
    const Context =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    return Context ? new LevelMeter(new Context()) : null;
  }

  /** Starts the audio clock. Call it inside a tap: iOS Safari keeps audio suspended otherwise. */
  wake(): void {
    void this.context.resume().catch(() => {});
  }

  /** Listens to a stream's microphone (replacing the last one). Nothing is played back. */
  connect(stream: MediaStream): void {
    this.source?.disconnect();
    this.source = stream.getAudioTracks().length
      ? this.context.createMediaStreamSource(stream)
      : null;
    this.source?.connect(this.analyser);
    this.wake();
  }

  /** The current level (RMS, 0…1). */
  level(): number {
    this.analyser.getFloatTimeDomainData(this.samples);
    return rms(this.samples);
  }

  close(): void {
    this.source?.disconnect();
    void this.context.close().catch(() => {});
  }
}

// ---------------------------------------------------------------------------------------------
// Camera: wave detection

/** Fractions of the frame, as the candidate sees it. */
export interface Region {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

/** Where the candidate waves: the top right of the preview, beside the outline (frame
 * DemoDeviceCheck's hand). */
export const WAVE_REGION: Region = { left: 0.68, top: 0.04, right: 0.98, bottom: 0.5 };

/** The preview is mirrored like a mirror, so its right is the camera frame's left. */
export function mirrorRegion(region: Region): Region {
  return { ...region, left: 1 - region.right, right: 1 - region.left };
}

/** A pixel counts as moving when its brightness changes by more than this (0–255). */
const PIXEL_CHANGE = 32;

/**
 * The share of pixels in `region` whose brightness changed between two greyscale frames of
 * `width` × `height`.
 */
export function regionMotion(
  previous: Uint8Array,
  next: Uint8Array,
  width: number,
  height: number,
  region: Region = { left: 0, top: 0, right: 1, bottom: 1 },
): number {
  const x0 = Math.floor(region.left * width);
  const x1 = Math.ceil(region.right * width);
  const y0 = Math.floor(region.top * height);
  const y1 = Math.ceil(region.bottom * height);
  let moved = 0;
  let total = 0;
  for (let y = y0; y < y1; y++) {
    for (let x = x0; x < x1; x++) {
      const index = y * width + x;
      if (Math.abs((next[index] ?? 0) - (previous[index] ?? 0)) > PIXEL_CHANGE) moved++;
      total++;
    }
  }
  return total ? moved / total : 0;
}

/** RGBA pixels to greyscale (Rec. 601 luma). */
export function toGrey(rgba: Uint8ClampedArray): Uint8Array {
  const grey = new Uint8Array(rgba.length / 4);
  for (let i = 0; i < grey.length; i++) {
    const p = i * 4;
    grey[i] = ((rgba[p] ?? 0) * 299 + (rgba[p + 1] ?? 0) * 587 + (rgba[p + 2] ?? 0) * 114) / 1000;
  }
  return grey;
}

/** Mean brightness (0–255) of a greyscale frame, or of a region of it. */
export function brightness(
  grey: Uint8Array,
  width: number,
  height: number,
  region: Region = { left: 0, top: 0, right: 1, bottom: 1 },
): number {
  const x0 = Math.max(0, Math.floor(region.left * width));
  const x1 = Math.min(width, Math.ceil(region.right * width));
  const y0 = Math.max(0, Math.floor(region.top * height));
  const y1 = Math.min(height, Math.ceil(region.bottom * height));
  let sum = 0;
  let total = 0;
  for (let y = y0; y < y1; y++) {
    for (let x = x0; x < x1; x++) {
      sum += grey[y * width + x] ?? 0;
      total++;
    }
  }
  return total ? sum / total : 0;
}

/** Movement in the wave region this large counts as a hand. */
const WAVE_MOTION = 0.08;
/** Whole-frame changes this large are the camera adjusting its exposure, not a hand. */
const GLOBAL_MOTION = 0.45;
/** A wave is several moving frames within a short window. */
const WAVE_FRAMES = 4;
const WAVE_WINDOW_MS = 1500;

/** Spots a wave: repeated movement in the wave region while the rest of the frame is calm. */
export class WaveDetector {
  private hits: number[] = [];

  /** One frame's motion: in the wave region, and over the whole frame. */
  add(regionShare: number, frameShare: number, at: number): boolean {
    this.hits = this.hits.filter((hit) => at - hit <= WAVE_WINDOW_MS);
    if (regionShare >= WAVE_MOTION && frameShare < GLOBAL_MOTION) this.hits.push(at);
    return this.hits.length >= WAVE_FRAMES;
  }
}

/** The "I can see myself" button appears after this long with the camera on (MEDIA.md §1). */
export const SEE_MYSELF_AFTER_MS = 5000;

// ---------------------------------------------------------------------------------------------
// Camera: face in frame

/** A detected face as fractions of the frame, as the candidate sees it. */
export interface FaceBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type FaceStatus = "ok" | "none" | "many" | "off_centre" | "too_far" | "dark";

/** Mean brightness (0–255) below which the face is too dark to see. */
export const DARK_BELOW = 55;

/** One face, roughly centred, big enough and lit well enough (MEDIA.md §1). */
export function judgeFace(faces: FaceBox[], faceBrightness: number): FaceStatus {
  const [face, another] = faces;
  if (!face) return "none";
  if (another) return "many";
  const centreX = face.x + face.width / 2;
  const centreY = face.y + face.height / 2;
  if (Math.abs(centreX - 0.5) > 0.2 || Math.abs(centreY - 0.5) > 0.25) return "off_centre";
  if (face.width < 0.12) return "too_far";
  if (faceBrightness < DARK_BELOW) return "dark";
  return "ok";
}

/** The camera check passes on a wave with the face in frame, or when the candidate confirms
 * they can see themselves (the fallback when detection can't tell). A face detector that
 * couldn't load leaves the wave alone. */
export function cameraPassed(check: {
  waved: boolean;
  face: FaceStatus | "unknown";
  confirmed: boolean;
}): boolean {
  if (check.confirmed) return true;
  return check.waved && (check.face === "ok" || check.face === "unknown");
}

export interface FaceFinder {
  /** Faces in the current video frame, in the camera's own (unmirrored) coordinates. */
  detect(video: HTMLVideoElement, at: number): FaceBox[];
  close(): void;
}

/** Where the MediaPipe WebAssembly files and face model are served (scripts/copy-mediapipe.mjs). */
export const MEDIAPIPE_PATH = "/mediapipe";

/**
 * MediaPipe Face Detection (BlazeFace short range), run on the device. Null when it can't load
 * (old browser, no WebAssembly); the camera check then relies on the wave and the fallback.
 */
export async function loadFaceFinder(): Promise<FaceFinder | null> {
  try {
    const { FaceDetector, FilesetResolver } = await import("@mediapipe/tasks-vision");
    const fileset = await FilesetResolver.forVisionTasks(MEDIAPIPE_PATH);
    const detector = await FaceDetector.createFromOptions(fileset, {
      baseOptions: {
        modelAssetPath: `${MEDIAPIPE_PATH}/blaze_face_short_range.tflite`,
        delegate: "CPU",
      },
      runningMode: "VIDEO",
      minDetectionConfidence: 0.6,
    });
    return {
      detect(video, at) {
        const width = video.videoWidth;
        const height = video.videoHeight;
        if (!width || !height) return [];
        return detector.detectForVideo(video, at).detections.flatMap((detection) => {
          const box = detection.boundingBox;
          return box
            ? [
                {
                  x: box.originX / width,
                  y: box.originY / height,
                  width: box.width / width,
                  height: box.height / height,
                },
              ]
            : [];
        });
      },
      close() {
        detector.close();
      },
    };
  } catch {
    return null;
  }
}

/** A face from the camera's coordinates to the mirrored preview's. */
export function mirrorFace(face: FaceBox): FaceBox {
  return { ...face, x: 1 - face.x - face.width };
}

// ---------------------------------------------------------------------------------------------
// The whole check

/** "Start interview" is enabled once every check has passed and every required box is ticked. */
export function readyToStart(check: {
  video: boolean;
  cameraOk: boolean;
  microphoneOk: boolean;
  consent: boolean;
  faceCheck: boolean;
  biometricConsent: boolean;
}): boolean {
  return (
    (!check.video || check.cameraOk) &&
    check.microphoneOk &&
    check.consent &&
    (!check.faceCheck || check.biometricConsent)
  );
}

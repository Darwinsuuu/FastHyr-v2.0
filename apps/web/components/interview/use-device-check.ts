"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  brightness,
  cameraPassed,
  type DeviceKind,
  type DeviceOption,
  deviceIdOf,
  type FaceBox,
  type FaceFinder,
  type FaceStatus,
  judgeFace,
  LevelMeter,
  listDevices,
  loadFaceFinder,
  type MediaProblem,
  mediaProblemOf,
  meterLevel,
  mirrorFace,
  mirrorRegion,
  openDevice,
  openStream,
  pickerFor,
  regionMotion,
  rememberDevice,
  rememberedDevice,
  SEE_MYSELF_AFTER_MS,
  SpeechCheck,
  stopStream,
  toGrey,
  WAVE_REGION,
  WaveDetector,
} from "@/lib/interview/devices";

export type CheckPhase = "intro" | "requesting" | "problem" | "checking" | "stopped";
export type MicStatus = "idle" | "listening" | "heard" | "too_quiet";

/** Bars in the level meter (frame DemoDeviceCheck). */
export const METER_BARS = 24;
const METER_EVERY_MS = 80;
// Camera frames are read small: enough for motion and light, cheap on phones.
const FRAME_WIDTH = 64;
const FRAME_HEIGHT = 48;
const FRAME_EVERY_MS = 100;
const FACE_EVERY_MS = 250;

export interface CameraState {
  /** "loading" while the face model starts; "unknown" when it can't run here. */
  face: FaceStatus | "unknown" | "loading";
  /** The face as the candidate sees it (mirrored), for the outline. */
  box: FaceBox | null;
  waved: boolean;
  canConfirm: boolean;
  passed: boolean;
}

const CAMERA_START: CameraState = {
  face: "loading",
  box: null,
  waved: false,
  canConfirm: false,
  passed: false,
};

/**
 * The device check's media (MEDIA.md §1): opens the camera (video interviews) and microphone
 * after the candidate taps Allow, runs the meter, the read-aloud, wave and face checks on the
 * device, and stops everything on `stop()` or unmount. Nothing is recorded or uploaded.
 */
export function useDeviceCheck(video: boolean) {
  const [phase, setPhase] = useState<CheckPhase>("intro");
  const [problem, setProblem] = useState<MediaProblem | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [devices, setDevices] = useState<Record<DeviceKind, DeviceOption[]>>({
    camera: [],
    microphone: [],
  });
  const [selected, setSelected] = useState<Record<DeviceKind, string | null>>({
    camera: null,
    microphone: null,
  });
  const [camera, setCamera] = useState<CameraState>(CAMERA_START);
  const [mic, setMic] = useState<MicStatus>("idle");
  const [levels, setLevels] = useState<number[]>(() => Array(METER_BARS).fill(0));

  const streamRef = useRef<MediaStream | null>(null);
  const meterRef = useRef<LevelMeter | null>(null);
  const speechRef = useRef<SpeechCheck | null>(null);
  const finderRef = useRef<FaceFinder | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const refreshDevices = useCallback(async (current: MediaStream) => {
    try {
      const all = await listDevices();
      const camera = pickerFor(all, "camera", deviceIdOf(current.getVideoTracks()[0]));
      const microphone = pickerFor(all, "microphone", deviceIdOf(current.getAudioTracks()[0]));
      setDevices({ camera: camera.options, microphone: microphone.options });
      setSelected({ camera: camera.selected, microphone: microphone.selected });
    } catch {
      // The pickers stay hidden; the default devices still work.
    }
  }, []);

  const release = useCallback(() => {
    stopStream(streamRef.current);
    streamRef.current = null;
    meterRef.current?.close();
    meterRef.current = null;
    setStream(null);
  }, []);

  /** Asks for the devices. Call it from the tap: iOS Safari only starts audio inside one. */
  const allow = useCallback(async () => {
    setPhase("requesting");
    setProblem(null);
    release();
    const meter = LevelMeter.create();
    meter?.wake();
    meterRef.current = meter;
    let opened: MediaStream;
    try {
      opened = await openStream(video, {
        camera: rememberedDevice("camera"),
        microphone: rememberedDevice("microphone"),
      });
    } catch (error) {
      meter?.close();
      meterRef.current = null;
      setProblem(mediaProblemOf(error));
      setPhase("problem");
      return;
    }
    streamRef.current = opened;
    meter?.connect(opened);
    setStream(opened);
    setCamera(CAMERA_START);
    setMic("idle");
    setPhase("checking");
    void refreshDevices(opened);
  }, [video, release, refreshDevices]);

  /** Switches to another camera or microphone; that device's check starts again. */
  const choose = useCallback(
    async (kind: DeviceKind, deviceId: string) => {
      const current = streamRef.current;
      if (!current || deviceId === selected[kind]) return;
      const old = kind === "camera" ? current.getVideoTracks() : current.getAudioTracks();
      // Phones often allow one camera at a time: free it before opening the next.
      old.forEach((track) => {
        track.stop();
        current.removeTrack(track);
      });
      let track: MediaStreamTrack;
      try {
        track = await openDevice(kind, deviceId);
      } catch (error) {
        setProblem(mediaProblemOf(error));
        setPhase("problem");
        release();
        return;
      }
      rememberDevice(kind, deviceId);
      const next = new MediaStream([...current.getTracks(), track]);
      streamRef.current = next;
      setStream(next);
      setSelected((was) => ({ ...was, [kind]: deviceId }));
      if (kind === "camera") {
        setCamera((was) => ({ ...CAMERA_START, face: finderRef.current ? "none" : was.face }));
      } else {
        meterRef.current?.connect(next);
        speechRef.current = null;
        setMic("idle");
      }
    },
    [selected, release],
  );

  /** "Start reading": listens for 2 s of speech while the candidate reads the sentence. */
  const listen = useCallback(() => {
    meterRef.current?.wake();
    speechRef.current = new SpeechCheck();
    setMic("listening");
  }, []);

  /** "I can see myself": the fallback when detection can't tell. */
  const confirmCamera = useCallback(() => {
    setCamera((was) => ({ ...was, passed: true }));
  }, []);

  /** Stops the camera and microphone (on Start, or when leaving the check). */
  const stop = useCallback(() => {
    release();
    setPhase("stopped");
  }, [release]);

  // Show the stream in the preview.
  useEffect(() => {
    const element = videoRef.current;
    if (element && element.srcObject !== stream) element.srcObject = stream;
  });

  // The meter and the read-aloud check.
  useEffect(() => {
    if (!stream) return;
    let last = performance.now();
    const timer = window.setInterval(() => {
      const meter = meterRef.current;
      if (!meter) return;
      const now = performance.now();
      const level = meter.level();
      setLevels((was) => [...was.slice(1), meterLevel(level)]);
      const speech = speechRef.current;
      if (speech) {
        const result = speech.add(level, now - last);
        if (result !== "listening") {
          speechRef.current = null;
          setMic(result);
        }
      }
      last = now;
    }, METER_EVERY_MS);
    return () => window.clearInterval(timer);
  }, [stream]);

  // The camera's checks: motion in the wave region, the face and its light.
  const hasVideo = !!stream && stream.getVideoTracks().length > 0;
  useEffect(() => {
    if (!hasVideo) return;
    let cancelled = false;
    const canvas = document.createElement("canvas");
    canvas.width = FRAME_WIDTH;
    canvas.height = FRAME_HEIGHT;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    const wave = new WaveDetector();
    const waveRegion = mirrorRegion(WAVE_REGION);
    let previous: Uint8Array | null = null;
    let faces: FaceBox[] | null = null;
    let lastFace = 0;
    const startedAt = performance.now();

    if (!finderRef.current) {
      void loadFaceFinder().then((finder) => {
        if (cancelled) {
          finder?.close();
          return;
        }
        finderRef.current = finder;
        if (!finder) setCamera((was) => ({ ...was, face: "unknown" }));
      });
    }

    const timer = window.setInterval(() => {
      const element = videoRef.current;
      if (!context || !element || element.readyState < 2) return;
      const now = performance.now();
      context.drawImage(element, 0, 0, FRAME_WIDTH, FRAME_HEIGHT);
      const grey = toGrey(context.getImageData(0, 0, FRAME_WIDTH, FRAME_HEIGHT).data);
      let waved = false;
      if (previous) {
        const inRegion = regionMotion(previous, grey, FRAME_WIDTH, FRAME_HEIGHT, waveRegion);
        const overall = regionMotion(previous, grey, FRAME_WIDTH, FRAME_HEIGHT);
        waved = wave.add(inRegion, overall, now);
      }
      previous = grey;

      const finder = finderRef.current;
      if (finder && now - lastFace >= FACE_EVERY_MS) {
        lastFace = now;
        try {
          faces = finder.detect(element, now);
        } catch {
          faces = null;
        }
      }
      // One face: its own light; otherwise the whole frame's.
      const only = faces?.length === 1 ? faces[0] : undefined;
      const face: FaceStatus | null = faces
        ? judgeFace(
            faces.map(mirrorFace),
            brightness(
              grey,
              FRAME_WIDTH,
              FRAME_HEIGHT,
              only && {
                left: only.x,
                top: only.y,
                right: only.x + only.width,
                bottom: only.y + only.height,
              },
            ),
          )
        : null;
      const box = only ? mirrorFace(only) : null;
      const canConfirm = now - startedAt >= SEE_MYSELF_AFTER_MS;

      setCamera((was) => {
        const next: CameraState = {
          face: face ?? (was.face === "loading" || was.face === "unknown" ? was.face : "none"),
          box,
          waved: was.waved || waved,
          canConfirm: was.canConfirm || canConfirm,
          passed: was.passed,
        };
        next.passed =
          was.passed ||
          cameraPassed({
            waved: next.waved,
            face: next.face === "loading" ? "none" : next.face,
            confirmed: false,
          });
        const same =
          next.face === was.face &&
          next.waved === was.waved &&
          next.canConfirm === was.canConfirm &&
          next.passed === was.passed &&
          sameBox(next.box, was.box);
        return same ? was : next;
      });
    }, FRAME_EVERY_MS);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [hasVideo, stream]);

  // Leaving the page or the check stops everything.
  useEffect(
    () => () => {
      stopStream(streamRef.current);
      meterRef.current?.close();
      finderRef.current?.close();
      finderRef.current = null;
    },
    [],
  );

  // A device plugged in or out changes the pickers.
  useEffect(() => {
    if (!stream || !navigator.mediaDevices) return;
    const onChange = () => void refreshDevices(stream);
    navigator.mediaDevices.addEventListener("devicechange", onChange);
    return () => navigator.mediaDevices.removeEventListener("devicechange", onChange);
  }, [stream, refreshDevices]);

  return {
    phase,
    problem,
    stream,
    videoRef,
    devices,
    selected,
    camera,
    mic,
    levels,
    allow,
    choose,
    listen,
    confirmCamera,
    stop,
  };
}

function sameBox(a: FaceBox | null, b: FaceBox | null): boolean {
  if (!a || !b) return a === b;
  const close = (x: number, y: number) => Math.abs(x - y) < 0.02;
  return close(a.x, b.x) && close(a.y, b.y) && close(a.width, b.width);
}

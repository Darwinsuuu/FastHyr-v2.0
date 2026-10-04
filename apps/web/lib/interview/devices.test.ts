import { describe, expect, it } from "vitest";

import {
  browserOf,
  cameraPassed,
  judgeFace,
  mediaProblemOf,
  meterLevel,
  mirrorFace,
  mirrorRegion,
  pickerFor,
  readyToStart,
  regionMotion,
  rms,
  SPEECH_LEVEL,
  SpeechCheck,
  WAVE_REGION,
  WaveDetector,
} from "./devices";

describe("mediaProblemOf", () => {
  it("reads getUserMedia failures", () => {
    const problem = (name: string) => mediaProblemOf(Object.assign(new Error(), { name }));
    expect(problem("NotAllowedError")).toBe("denied");
    expect(problem("SecurityError")).toBe("denied");
    expect(problem("NotFoundError")).toBe("not_found");
    expect(problem("OverconstrainedError")).toBe("not_found");
    expect(problem("NotReadableError")).toBe("in_use");
    expect(problem("Unsupported")).toBe("unsupported");
    expect(problem("TypeError")).toBe("failed");
    expect(mediaProblemOf("nope")).toBe("failed");
  });
});

describe("browserOf", () => {
  const ua = {
    chrome:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36",
    edge: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36 Edg/141.0",
    firefox: "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0",
    safari:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Safari/605.1.15",
    iphone:
      "Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1",
    iphoneChrome:
      "Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/141.0 Mobile/15E148 Safari/604.1",
    android:
      "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Mobile Safari/537.36",
    linkedin:
      "Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 [LinkedInApp]",
  };

  it("picks the fix steps for each browser", () => {
    expect(browserOf(ua.chrome)).toBe("chrome");
    expect(browserOf(ua.edge)).toBe("edge");
    expect(browserOf(ua.firefox)).toBe("firefox");
    expect(browserOf(ua.safari)).toBe("safari");
    expect(browserOf(ua.iphone)).toBe("ios");
    expect(browserOf(ua.iphoneChrome)).toBe("iosApp");
    expect(browserOf(ua.android)).toBe("android");
    expect(browserOf(ua.linkedin)).toBe("inApp");
  });

  it("tells an iPad from a Mac by touch", () => {
    expect(browserOf(ua.safari, 5)).toBe("ios");
    expect(browserOf(ua.safari, 0)).toBe("safari");
  });
});

describe("pickerFor", () => {
  const all = [
    { kind: "audioinput", deviceId: "default", groupId: "g1", label: "Default - Mic A" },
    { kind: "audioinput", deviceId: "a", groupId: "g1", label: "Mic A" },
    { kind: "audioinput", deviceId: "b", groupId: "g2", label: "Mic B" },
    { kind: "videoinput", deviceId: "cam", groupId: "g3", label: "Camera" },
  ] as const;

  it("lists real devices once and maps Chrome's default alias to its device", () => {
    const picker = pickerFor([...all], "microphone", "default");
    expect(picker.options.map((o) => o.deviceId)).toEqual(["a", "b"]);
    expect(picker.selected).toBe("a");
    expect(pickerFor([...all], "camera", "cam").selected).toBe("cam");
  });

  it("keeps an alias it can't match so the picker is never blank", () => {
    const unmatched = [{ ...all[0], groupId: "other" }, all[1], all[2]];
    const picker = pickerFor(unmatched, "microphone", "default");
    expect(picker.options[0]?.deviceId).toBe("default");
    expect(picker.selected).toBe("default");
  });
});

describe("microphone", () => {
  it("measures the level", () => {
    expect(rms(new Float32Array([0.5, -0.5, 0.5, -0.5]))).toBeCloseTo(0.5);
    expect(rms(new Float32Array())).toBe(0);
    expect(meterLevel(0)).toBe(0);
    expect(meterLevel(0.001)).toBe(0);
    expect(meterLevel(1)).toBe(1);
    expect(meterLevel(0.03)).toBeGreaterThan(0.3);
  });

  it("passes after 2 s of speech-level sound, not on room noise", () => {
    const check = new SpeechCheck();
    for (let i = 0; i < 24; i++) expect(check.add(SPEECH_LEVEL / 3, 80)).toBe("listening");
    let result = "listening";
    for (let i = 0; i < 25 && result === "listening"; i++) result = check.add(0.05, 80);
    expect(result).toBe("heard");
    expect(check.heardMs).toBeGreaterThanOrEqual(2000);
  });

  it("asks for a fix when it hears too little", () => {
    const check = new SpeechCheck(2000, 1000);
    expect(check.add(0.05, 500)).toBe("listening");
    expect(check.add(0.001, 600)).toBe("too_quiet");
  });
});

describe("wave", () => {
  const width = 10;
  const height = 10;
  const frame = (moved: (x: number, y: number) => boolean) => {
    const pixels = new Uint8Array(width * height);
    for (let y = 0; y < height; y++)
      for (let x = 0; x < width; x++) pixels[y * width + x] = moved(x, y) ? 200 : 20;
    return pixels;
  };
  const still = frame(() => false);

  it("measures movement in a region", () => {
    const leftHalf = frame((x) => x < 5);
    expect(regionMotion(still, leftHalf, width, height)).toBeCloseTo(0.5);
    expect(
      regionMotion(still, leftHalf, width, height, { left: 0, top: 0, right: 0.5, bottom: 1 }),
    ).toBe(1);
    expect(
      regionMotion(still, leftHalf, width, height, { left: 0.5, top: 0, right: 1, bottom: 1 }),
    ).toBe(0);
  });

  it("mirrors the wave region: the preview's top right is the camera's top left", () => {
    const region = mirrorRegion(WAVE_REGION);
    expect(region.left).toBeCloseTo(1 - WAVE_REGION.right);
    expect(region.right).toBeCloseTo(1 - WAVE_REGION.left);
    expect(mirrorFace({ x: 0.1, y: 0.2, width: 0.3, height: 0.3 }).x).toBeCloseTo(0.6);
  });

  it("needs repeated movement in the region while the rest of the frame is calm", () => {
    const wave = new WaveDetector();
    expect(wave.add(0.3, 0.05, 0)).toBe(false);
    expect(wave.add(0.3, 0.05, 100)).toBe(false);
    expect(wave.add(0.3, 0.05, 200)).toBe(false);
    expect(wave.add(0.3, 0.05, 300)).toBe(true);

    // A camera adjusting its exposure moves the whole frame: not a wave.
    const lights = new WaveDetector();
    for (let at = 0; at < 1000; at += 100) expect(lights.add(0.9, 0.9, at)).toBe(false);

    // Twitches spread out over time aren't a wave either.
    const twitch = new WaveDetector();
    for (let at = 0; at < 8000; at += 2000) expect(twitch.add(0.3, 0.05, at)).toBe(false);
  });
});

describe("judgeFace", () => {
  const centred = { x: 0.35, y: 0.25, width: 0.3, height: 0.4 };

  it("wants one centred, close, well-lit face", () => {
    expect(judgeFace([centred], 120)).toBe("ok");
    expect(judgeFace([], 120)).toBe("none");
    expect(judgeFace([centred, { ...centred, x: 0 }], 120)).toBe("many");
    expect(judgeFace([{ ...centred, x: 0 }], 120)).toBe("off_centre");
    expect(judgeFace([{ x: 0.46, y: 0.45, width: 0.08, height: 0.1 }], 120)).toBe("too_far");
    expect(judgeFace([centred], 30)).toBe("dark");
  });
});

describe("cameraPassed and readyToStart", () => {
  it("passes the camera on a wave with a face, or the candidate's confirmation", () => {
    expect(cameraPassed({ waved: true, face: "ok", confirmed: false })).toBe(true);
    expect(cameraPassed({ waved: true, face: "none", confirmed: false })).toBe(false);
    expect(cameraPassed({ waved: false, face: "ok", confirmed: false })).toBe(false);
    // No face detector here: the wave is enough.
    expect(cameraPassed({ waved: true, face: "unknown", confirmed: false })).toBe(true);
    expect(cameraPassed({ waved: false, face: "none", confirmed: true })).toBe(true);
  });

  it("enables Start only with every check and required box", () => {
    const all = {
      video: true,
      cameraOk: true,
      microphoneOk: true,
      consent: true,
      faceCheck: true,
      biometricConsent: true,
    };
    expect(readyToStart(all)).toBe(true);
    expect(readyToStart({ ...all, cameraOk: false })).toBe(false);
    expect(readyToStart({ ...all, microphoneOk: false })).toBe(false);
    expect(readyToStart({ ...all, consent: false })).toBe(false);
    expect(readyToStart({ ...all, biometricConsent: false })).toBe(false);
    // Voice only: no camera, no face check.
    expect(
      readyToStart({
        ...all,
        video: false,
        cameraOk: false,
        faceCheck: false,
        biometricConsent: false,
      }),
    ).toBe(true);
  });
});

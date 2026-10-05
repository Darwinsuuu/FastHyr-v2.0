"use client";

import {
  CheckCircleIcon,
  HandWavingIcon,
  MicrophoneIcon,
  VideoCameraIcon,
  WarningCircleIcon,
} from "@phosphor-icons/react";
import { useRouter } from "next/navigation";
import { type ReactNode, useId, useState } from "react";

import { ConsentCheckbox } from "@/components/consent/consent-checkbox";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { api, ApiError, unwrap } from "@/lib/api/client";
import { cn } from "@/lib/cn";
import { t, type MessageKey } from "@/lib/i18n";
import type { InterviewLink } from "@/lib/interview";
import {
  type BrowserKind,
  browserOf,
  type DeviceKind,
  type DeviceOption,
  type MediaProblem,
  readyToStart,
} from "@/lib/interview/devices";
import type { Notice } from "@/lib/notices";

import { type CameraState, type MicStatus, useDeviceCheck } from "./use-device-check";
import type { InterviewDevices } from "./use-interview-session";

export interface DeviceCheckNotices {
  interview: Notice;
  biometric: Notice;
}

/**
 * The device check (INTV-003, FR-INTV-03, frame DemoDeviceCheck without the demo toggle): asks
 * for the camera (video interviews) and microphone after saying why, checks both on the device,
 * and takes the interview consent (plus the face-check consent when `face_check`). "Start
 * interview" records the consent, stops the check's devices and hands the chosen ones to the
 * live interview (INTV-005).
 * Mobile first: the cards stack, and sit side by side from `lg`.
 */
export function DeviceCheck({
  token,
  link,
  notices,
  onBack,
  onStarted,
}: {
  token: string;
  link: InterviewLink;
  /** Null when the notices couldn't load: the check says so instead of a consent. */
  notices: DeviceCheckNotices | null;
  onBack: () => void;
  /** Consent is recorded: the live interview starts with these devices. */
  onStarted: (devices: InterviewDevices) => void;
}) {
  const router = useRouter();
  const video = link.format === "video_voice";
  const check = useDeviceCheck(video);
  const [consent, setConsent] = useState(false);
  const [biometric, setBiometric] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<"failed" | "outdated" | null>(null);
  const hintId = useId();

  const ready = readyToStart({
    video,
    cameraOk: check.camera.passed,
    microphoneOk: check.mic === "heard",
    consent,
    faceCheck: link.face_check,
    biometricConsent: biometric,
  });

  async function start() {
    if (!notices || !ready) return;
    setSaving(true);
    setError(null);
    try {
      unwrap(
        await api.POST("/v1/candidate/interviews/{token}/consent", {
          params: { path: { token } },
          body: {
            consent_notice_id: notices.interview.id,
            biometric_notice_id: link.face_check ? notices.biometric.id : null,
          },
        }),
      );
    } catch (failure) {
      setSaving(false);
      if (failure instanceof ApiError && failure.code === "notice_outdated") {
        // Fresh words from the server; the candidate reads and ticks them again.
        setConsent(false);
        setBiometric(false);
        setError("outdated");
        router.refresh();
      } else if (
        failure instanceof ApiError &&
        (failure.status === 404 || failure.status === 409)
      ) {
        // The link changed state (expired, closed): the page shows the new one.
        check.stop();
        router.refresh();
      } else {
        setError("failed");
      }
      return;
    }
    const devices = { camera: check.selected.camera, microphone: check.selected.microphone };
    check.stop();
    onStarted(devices);
  }

  if (check.phase === "stopped") return null;

  const values = { company: link.company.name };
  const showCheck = check.phase === "checking";

  return (
    <div
      className={cn(
        "flex w-full flex-col gap-6 md:gap-7",
        video && showCheck ? "max-w-[640px] lg:max-w-[1180px]" : "max-w-[640px]",
      )}
    >
      <div className="flex flex-col gap-2 text-center">
        <p className="text-[12px] leading-4 font-semibold tracking-[0.08em] text-ink-muted uppercase">
          {t("interview.check.eyebrow")}
        </p>
        <h1 className="type-display-lg break-words">
          {t(video ? "interview.check.titleVideo" : "interview.check.titleVoice")}
        </h1>
        <p className="type-body mx-auto max-w-[640px] text-ink-muted">
          {t(video ? "interview.check.subtitleVideo" : "interview.check.subtitleVoice")}
        </p>
      </div>

      {check.phase === "intro" || check.phase === "requesting" ? (
        <Card>
          <span
            aria-hidden="true"
            className="flex size-12 items-center justify-center rounded-md bg-surface-sunk text-ink [&_svg]:size-6"
          >
            {video ? <VideoCameraIcon /> : <MicrophoneIcon />}
          </span>
          <div className="type-body flex flex-col gap-2">
            <p>{t(video ? "interview.check.allowBodyVideo" : "interview.check.allowBodyVoice")}</p>
            <p className="text-ink-muted">{t("interview.check.private")}</p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Button
              side="candidate"
              size="lg"
              loading={check.phase === "requesting"}
              onClick={() => void check.allow()}
              className="w-full sm:w-auto"
            >
              {t(video ? "interview.check.allowVideo" : "interview.check.allowVoice")}
            </Button>
            <Button variant="quiet" side="candidate" size="lg" onClick={onBack}>
              {t("interview.check.back")}
            </Button>
          </div>
        </Card>
      ) : check.phase === "problem" && check.problem ? (
        <ProblemCard
          problem={check.problem}
          video={video}
          onRetry={() => void check.allow()}
          onBack={onBack}
        />
      ) : (
        <>
          <div className={cn("grid gap-4 md:gap-6", video && "lg:grid-cols-2")}>
            {video && (
              <CameraCard
                camera={check.camera}
                videoRef={check.videoRef}
                devices={check.devices.camera}
                selected={check.selected.camera}
                onChoose={(id) => void check.choose("camera", id)}
                onConfirm={check.confirmCamera}
              />
            )}
            <MicrophoneCard
              number={video ? 2 : 1}
              status={check.mic}
              levels={check.levels}
              devices={check.devices.microphone}
              selected={check.selected.microphone}
              onChoose={(id) => void check.choose("microphone", id)}
              onListen={check.listen}
            />
          </div>

          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between lg:gap-8">
            {notices ? (
              <div className="flex max-w-[640px] flex-col gap-3">
                <ConsentCheckbox
                  variant="plain"
                  notice={notices.interview}
                  values={values}
                  checked={consent}
                  onCheckedChange={setConsent}
                />
                {link.face_check && (
                  <ConsentCheckbox
                    variant="plain"
                    notice={notices.biometric}
                    values={values}
                    checked={biometric}
                    onCheckedChange={setBiometric}
                  />
                )}
              </div>
            ) : (
              <Alert>{t("interview.check.noticesFailed")}</Alert>
            )}
            <div className="flex shrink-0 flex-col gap-2 lg:items-end">
              {error && (
                <Alert>
                  {t(
                    error === "outdated"
                      ? "interview.check.consentOutdated"
                      : "interview.check.consentFailed",
                  )}
                </Alert>
              )}
              <Button
                side="candidate"
                size="lg"
                disabled={!ready || !notices}
                loading={saving}
                aria-describedby={ready ? undefined : hintId}
                onClick={() => void start()}
                className="w-full lg:w-auto lg:px-8"
              >
                {t("interview.check.start")}
              </Button>
              {!ready && (
                <p id={hintId} className="text-[13px] leading-5 text-ink-muted">
                  {t(
                    !video
                      ? "interview.check.notReadyVoice"
                      : link.face_check
                        ? "interview.check.notReadyBoxes"
                        : "interview.check.notReadyVideo",
                  )}
                </p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function CameraCard({
  camera,
  videoRef,
  devices,
  selected,
  onChoose,
  onConfirm,
}: {
  camera: CameraState;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  devices: DeviceOption[];
  selected: string | null;
  onChoose: (deviceId: string) => void;
  onConfirm: () => void;
}) {
  const faceKey = `interview.check.camera.face.${camera.face}` as MessageKey;
  return (
    <CheckCard
      number={1}
      title={t("interview.check.camera.title")}
      done={camera.passed}
      status={t(
        camera.passed ? "interview.check.camera.working" : "interview.check.camera.waiting",
      )}
    >
      <div className="relative aspect-[4/3] overflow-hidden rounded-md bg-on-marigold lg:aspect-auto lg:h-[300px]">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          aria-label={t("interview.check.camera.preview")}
          className="size-full -scale-x-100 object-cover"
        />
        <div
          aria-hidden="true"
          className={cn(
            "pointer-events-none absolute inset-y-[8%] left-1/2 aspect-[3/4] -translate-x-1/2 rounded-[50%/45%] border-2",
            camera.face === "ok" || camera.passed
              ? "border-solid border-marigold"
              : "border-dashed border-marigold/60",
          )}
        />
        {!camera.passed && (
          <HandWavingIcon
            aria-hidden="true"
            className="absolute top-4 right-5 size-10 origin-[50%_90%] animate-[fh-wave_800ms_ease-in-out_infinite] text-marigold motion-reduce:animate-none"
          />
        )}
        <DeviceLabel devices={devices} selected={selected} kind="camera" />
      </div>
      <p className="type-body">
        <span className="font-bold">{t("interview.check.camera.waveLead")}</span>{" "}
        {t("interview.check.camera.waveBody")}
      </p>
      {camera.face !== "unknown" && !camera.passed && (
        <p aria-live="polite" className="text-[14px] leading-5 text-ink-muted">
          {t(faceKey)}
        </p>
      )}
      {camera.passed ? (
        <DoneButton>{t("interview.check.camera.seen")}</DoneButton>
      ) : (
        camera.canConfirm && (
          <Button variant="secondary" side="candidate" size="lg" onClick={onConfirm}>
            {t("interview.check.camera.seeMyself")}
          </Button>
        )
      )}
      <DevicePicker kind="camera" devices={devices} selected={selected} onChoose={onChoose} />
    </CheckCard>
  );
}

function MicrophoneCard({
  number,
  status,
  levels,
  devices,
  selected,
  onChoose,
  onListen,
}: {
  number: number;
  status: MicStatus;
  levels: number[];
  devices: DeviceOption[];
  selected: string | null;
  onChoose: (deviceId: string) => void;
  onListen: () => void;
}) {
  const heard = status === "heard";
  const listening = status === "listening";
  const hint = {
    idle: "interview.check.mic.idle",
    listening: "interview.check.mic.hintListening",
    heard: "interview.check.mic.heard",
    too_quiet: "interview.check.mic.tooQuiet",
  } as const satisfies Record<MicStatus, MessageKey>;
  return (
    <CheckCard
      number={number}
      title={t("interview.check.mic.title")}
      done={heard}
      status={t(
        heard
          ? "interview.check.mic.working"
          : listening
            ? "interview.check.mic.listening"
            : "interview.check.mic.notTested",
      )}
    >
      <div className="flex flex-col gap-2.5 rounded-md bg-surface-sunk px-4 py-4 md:px-6 md:py-5">
        <p className="text-[12px] leading-4 font-semibold tracking-[0.08em] text-ink-muted uppercase">
          {t("interview.check.mic.readThis")}
        </p>
        <p className="font-display text-[19px] leading-[1.5] text-ink md:text-[22px]">
          {t("interview.check.mic.sentence")}
        </p>
      </div>
      <div className="flex items-center gap-3">
        <MicrophoneIcon aria-hidden="true" className="size-5 shrink-0 text-ink" />
        <div aria-hidden="true" className="flex h-8 min-w-0 grow items-end gap-[3px]">
          {levels.map((level, index) => (
            <span
              key={index}
              className={cn(
                "min-w-0 flex-1 rounded-[2px] transition-[height] duration-75",
                heard ? "bg-evergreen" : listening ? "bg-persimmon" : "bg-line-strong",
              )}
              style={{ height: `${Math.max(4, Math.round(level * 32))}px` }}
            />
          ))}
        </div>
      </div>
      <p
        aria-live="polite"
        className={cn(
          "text-[14px] leading-5",
          status === "too_quiet" ? "text-ink" : "text-ink-muted",
        )}
      >
        {t(hint[status])}
      </p>
      {heard ? (
        <DoneButton>{t("interview.check.mic.done")}</DoneButton>
      ) : (
        <Button
          variant="secondary"
          side="candidate"
          size="lg"
          loading={listening}
          onClick={onListen}
        >
          {t(status === "too_quiet" ? "interview.check.mic.retry" : "interview.check.mic.start")}
        </Button>
      )}
      <DevicePicker kind="microphone" devices={devices} selected={selected} onChoose={onChoose} />
    </CheckCard>
  );
}

function CheckCard({
  number,
  title,
  done,
  status,
  children,
}: {
  number: number;
  title: string;
  done: boolean;
  status: string;
  children: ReactNode;
}) {
  return (
    <section className="flex min-w-0 flex-col gap-4 rounded-lg border border-line bg-surface-raised p-4 shadow-raised md:gap-[18px] md:p-7">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <span className="text-[12px] font-bold text-ink-muted">{number}</span>
          <h2 className="text-[18px] leading-6 font-bold">{title}</h2>
        </div>
        <span aria-live="polite">
          <Badge
            tone={done ? "evergreen" : "neutral"}
            icon={done ? <CheckCircleIcon /> : undefined}
          >
            {status}
          </Badge>
        </span>
      </div>
      {children}
    </section>
  );
}

/** The device in use, over the preview (frame DemoDeviceCheck). */
function DeviceLabel({
  devices,
  selected,
  kind,
}: {
  devices: DeviceOption[];
  selected: string | null;
  kind: DeviceKind;
}) {
  const index = devices.findIndex((device) => device.deviceId === selected);
  const device = devices[index];
  if (!device) return null;
  return (
    <span className="absolute bottom-3 left-3 max-w-[calc(100%-24px)] truncate rounded-pill bg-surface-raised/90 px-2.5 py-1 text-[13px] leading-4 text-ink">
      {deviceName(device, index, kind)}
    </span>
  );
}

/** A picker when there is more than one camera or microphone; the choice is remembered. */
function DevicePicker({
  kind,
  devices,
  selected,
  onChoose,
}: {
  kind: DeviceKind;
  devices: DeviceOption[];
  selected: string | null;
  onChoose: (deviceId: string) => void;
}) {
  if (devices.length < 2) return null;
  return (
    <Field
      label={t(kind === "camera" ? "interview.check.camera.picker" : "interview.check.mic.picker")}
    >
      <Select
        size="sm"
        value={selected ?? undefined}
        onValueChange={onChoose}
        options={devices.map((device, index) => ({
          value: device.deviceId,
          label: deviceName(device, index, kind),
        }))}
      />
    </Field>
  );
}

function deviceName(device: DeviceOption, index: number, kind: DeviceKind): string {
  return (
    device.label ||
    t(kind === "camera" ? "interview.check.camera.unnamed" : "interview.check.mic.unnamed", {
      count: index + 1,
    })
  );
}

function DoneButton({ children }: { children: ReactNode }) {
  return (
    <p className="flex min-h-12 items-center justify-center gap-2 rounded-md border border-evergreen bg-evergreen-soft px-6 text-[15px] leading-5 font-semibold text-evergreen">
      <CheckCircleIcon aria-hidden="true" className="size-5" />
      {children}
    </p>
  );
}

const HELP_STEPS = ["1", "2", "3"] as const;

function ProblemCard({
  problem,
  video,
  onRetry,
  onBack,
}: {
  problem: MediaProblem;
  video: boolean;
  onRetry: () => void;
  onBack: () => void;
}) {
  const [browser] = useState<BrowserKind>(() =>
    browserOf(navigator.userAgent, navigator.maxTouchPoints),
  );
  const devices = t(
    video ? "interview.check.problem.devicesVideo" : "interview.check.problem.devicesVoice",
  );
  const unsupported = problem === "unsupported" || (problem === "denied" && browser === "inApp");
  const title = unsupported
    ? t("interview.check.problem.unsupportedTitle")
    : problem === "failed"
      ? t("interview.check.problem.failedTitle")
      : t(`interview.check.problem.${problem}${video ? "Video" : "Voice"}` as MessageKey);
  const body = unsupported
    ? t("interview.check.problem.unsupportedBody")
    : problem === "failed"
      ? t("interview.check.problem.failedBody")
      : t(`interview.check.problem.${problem}Body` as MessageKey);

  return (
    <Card role="alert">
      <span
        aria-hidden="true"
        className="flex size-12 items-center justify-center rounded-md bg-surface-sunk text-signal-gap [&_svg]:size-6"
      >
        <WarningCircleIcon />
      </span>
      <h2 className="type-heading">{title}</h2>
      <p className="type-body">{body}</p>
      {problem === "denied" && !unsupported && (
        <>
          <ol className="type-body flex list-decimal flex-col gap-1.5 pl-6">
            {HELP_STEPS.map((step) => (
              <li key={step}>
                {t(`interview.check.help.${browser}.${step}` as MessageKey, { devices })}
              </li>
            ))}
          </ol>
          <p className="text-[14px] leading-5 text-ink-muted">
            {t("interview.check.problem.system")}
          </p>
        </>
      )}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Button side="candidate" size="lg" onClick={onRetry} className="w-full sm:w-auto">
          {t("interview.check.problem.retry")}
        </Button>
        <Button variant="quiet" side="candidate" size="lg" onClick={onBack}>
          {t("interview.check.back")}
        </Button>
      </div>
    </Card>
  );
}

function Card({
  children,
  className,
  role,
}: {
  children: ReactNode;
  className?: string;
  role?: "alert";
}) {
  return (
    <section
      role={role}
      className={cn(
        "mx-auto flex w-full flex-col gap-5 rounded-lg border border-line bg-surface-raised p-6 shadow-raised md:gap-6 md:p-10",
        className,
      )}
    >
      {children}
    </section>
  );
}

function Alert({ children }: { children: ReactNode }) {
  return (
    <p
      role="alert"
      className="flex gap-2.5 rounded-md border border-signal-gap bg-surface-raised px-3.5 py-3 text-[14px] leading-5"
    >
      <WarningCircleIcon
        aria-hidden="true"
        className="mt-px size-[18px] shrink-0 text-signal-gap"
      />
      {children}
    </p>
  );
}

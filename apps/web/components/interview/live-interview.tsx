"use client";

import {
  ClockIcon,
  MicrophoneIcon,
  MicrophoneSlashIcon,
  UserIcon,
  WarningCircleIcon,
  WifiSlashIcon,
} from "@phosphor-icons/react";
import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";

import { InterviewHeader } from "@/components/interview/interview-header";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/cn";
import { plural, t } from "@/lib/i18n";
import type { InterviewCompany } from "@/lib/interview";
import type { InterviewClient } from "@/lib/interview/client";
import {
  ANNOUNCE_AT_MINUTES,
  type CaptionLine,
  clock,
  currentLine,
  interviewerStatus,
  LOW_TIME_SECONDS,
  type SessionState,
  type SessionTopic,
  visibleCaptions,
} from "@/lib/interview/session";

import { type InterviewDevices, useInterviewSession } from "./use-interview-session";

/**
 * The live interview (INTV-005, FR-INTV-04, frame DemoInterview): the interviewer's status and
 * current line, "From your résumé", live captions, Mute, End interview (with a confirm), time
 * remaining and self-view, with the topics and tips beside it from `lg`. Mobile first: one
 * column with the controls pinned to the bottom of the screen and a small self-view. When the
 * session ends, `onEnded` hands back to the link page.
 */
export function LiveInterview({
  company,
  jobTitle,
  video,
  devices,
  client,
  allowFake,
  onEnded,
}: {
  company: InterviewCompany;
  jobTitle: string;
  video: boolean;
  devices: InterviewDevices;
  client: InterviewClient;
  allowFake: boolean;
  onEnded: () => void;
}) {
  const session = useInterviewSession({ client, video, devices, allowFake, onEnded });
  const { state } = session;
  const inCall = state.phase !== "failed" && state.phase !== "ended";

  return (
    <div className="flex min-h-dvh flex-col bg-surface lg:h-dvh">
      <InterviewHeader company={company}>
        {inCall && state.secondsLeft !== null && <TimeLeft seconds={state.secondsLeft} />}
        {inCall && (
          <span className="hidden items-center gap-2 text-[14px] leading-5 text-ink-muted md:inline-flex">
            <span aria-hidden="true" className="size-2 rounded-pill bg-persimmon" />
            {t("interview.live.liveRole", { title: jobTitle })}
          </span>
        )}
      </InterviewHeader>

      {state.phase === "failed" ? (
        <Centred>
          <FailedCard failure={state.failure ?? "connect"} video={video} onRetry={session.retry} />
        </Centred>
      ) : state.phase === "ended" ? (
        <Centred>
          <section
            aria-busy="true"
            className="flex w-full max-w-[640px] flex-col items-center gap-4 rounded-lg border border-line bg-surface-raised p-6 text-center shadow-raised md:p-10"
          >
            <Spinner />
            <h1 className="type-heading">{t("interview.live.finishing.title")}</h1>
            <p className="type-body text-ink-muted">{t("interview.live.finishing.body")}</p>
          </section>
        </Centred>
      ) : (
        <Stage
          state={state}
          company={company}
          video={video}
          stream={session.stream}
          onMute={session.setMuted}
          onEnd={session.end}
        />
      )}
    </div>
  );
}

function Stage({
  state,
  company,
  video,
  stream,
  onMute,
  onEnd,
}: {
  state: SessionState;
  company: InterviewCompany;
  video: boolean;
  stream: MediaStream | null;
  onMute: (muted: boolean) => void;
  onEnd: () => Promise<void>;
}) {
  const [confirming, setConfirming] = useState(false);
  const [endFailed, setEndFailed] = useState(false);
  const status = interviewerStatus(state);
  const line = currentLine(state);
  const captions = visibleCaptions(state);
  const topic = state.topics.find((item) => item.number === state.topicNumber);
  const canEnd = state.phase === "live" || state.phase === "reconnecting";

  async function end() {
    setEndFailed(false);
    try {
      await onEnd();
    } catch {
      setEndFailed(true);
      throw new Error("end failed");
    }
  }

  return (
    <main className="page-gutter flex flex-1 flex-col gap-4 pt-4 lg:min-h-0 lg:flex-row lg:gap-8 lg:pt-8 lg:pb-10">
      <section
        aria-labelledby="interviewer-name"
        className="flex min-w-0 flex-1 flex-col rounded-lg bg-surface-raised shadow-raised lg:min-h-0 lg:overflow-hidden"
      >
        <div className="flex flex-col gap-4 border-b border-line px-4 pt-5 pb-5 md:gap-5 md:px-8 md:pt-8 lg:px-12 lg:pt-10 lg:pb-7">
          <div className="flex items-start gap-3 md:gap-4">
            <SpeakingMark speaking={status === "speaking"} />
            <div className="flex min-w-0 flex-1 flex-col gap-0.5">
              <h1 id="interviewer-name" className="text-[16px] leading-6 font-bold">
                {t("interview.live.interviewer")}
              </h1>
              <p
                className={cn(
                  "text-[14px] leading-5",
                  status === "paused" ? "font-semibold text-persimmon-ink" : "text-ink-muted",
                )}
              >
                {t(`interview.live.status.${status}`)}
              </p>
              {topic && state.topics.length > 0 && (
                <p className="text-[13px] leading-5 text-ink-muted lg:hidden">
                  {t("interview.live.topicOf", {
                    number: topic.number,
                    total: state.topics.length,
                  })}
                  {" · "}
                  <span className="text-ink">{topic.title}</span>
                </p>
              )}
            </div>
            <SelfView
              video={video}
              stream={stream}
              muted={state.muted}
              className="h-[88px] w-[66px] shrink-0 md:h-[120px] md:w-[90px] lg:hidden"
              compact
            />
          </div>

          {state.phase === "reconnecting" && <Reconnecting />}

          <p
            key={line?.id ?? "waiting"}
            className={cn(
              "animate-[fh-rise_320ms_ease-out] font-display text-[22px] leading-[1.35] font-[450] tracking-[-0.01em] break-words motion-reduce:animate-none md:text-[28px] lg:text-[34px] lg:leading-[1.3]",
              !line && "text-ink-muted",
            )}
          >
            {line?.text ?? t("interview.live.startingSoon")}
          </p>
          {state.quote && (
            <p className="text-[14px] leading-6 text-ink-muted">
              {t("interview.live.fromResume")}{" "}
              <span className="type-mono bg-marigold px-1 py-px text-on-marigold">
                {state.quote}
              </span>
            </p>
          )}
        </div>

        <Captions lines={captions} />

        <div className="sticky bottom-0 z-10 flex items-center justify-between gap-3 rounded-b-lg border-t border-line bg-surface-raised px-4 pt-3 pb-[max(12px,env(safe-area-inset-bottom))] md:px-8 lg:static lg:px-12 lg:py-[18px]">
          <div className="flex min-w-0 items-center gap-3">
            <Button
              variant="secondary"
              side="candidate"
              size="lg"
              aria-pressed={state.muted}
              icon={state.muted ? <MicrophoneSlashIcon /> : <MicrophoneIcon />}
              onClick={() => onMute(!state.muted)}
            >
              {state.muted ? t("interview.live.unmute") : t("interview.live.mute")}
            </Button>
            <span className="hidden text-[14px] leading-5 text-ink-muted md:inline lg:hidden xl:inline">
              {state.muted ? t("interview.live.mutedHint") : t("interview.live.muteHint")}
            </span>
          </div>
          <Button
            side="candidate"
            size="lg"
            disabled={!canEnd}
            loading={state.phase === "ending"}
            onClick={() => setConfirming(true)}
          >
            {t("interview.live.end")}
          </Button>
        </div>
      </section>

      <aside className="flex flex-col gap-4 pb-8 lg:w-[320px] lg:shrink-0 lg:gap-5 lg:overflow-y-auto lg:pb-0">
        <SelfView
          video={video}
          stream={stream}
          muted={state.muted}
          className="hidden h-[220px] lg:flex"
        />
        {state.topics.length > 0 && <Topics topics={state.topics} current={state.topicNumber} />}
        <Panel title={t("interview.live.tips.title")}>
          <ul className="flex list-disc flex-col gap-2 pl-[18px] text-[14px] leading-[1.5]">
            <li>{t("interview.live.tips.1")}</li>
            <li>{t("interview.live.tips.2")}</li>
            <li>{t("interview.live.tips.3")}</li>
          </ul>
        </Panel>
      </aside>

      <ConfirmDialog
        open={confirming}
        onOpenChange={(open) => {
          setConfirming(open);
          if (!open) setEndFailed(false);
        }}
        side="candidate"
        title={t("interview.live.endConfirm.title")}
        description={t("interview.live.endConfirm.body", { company: company.name })}
        confirmLabel={t("interview.live.endConfirm.confirm")}
        cancelLabel={t("interview.live.endConfirm.cancel")}
        onConfirm={end}
      >
        {endFailed && <Alert>{t("interview.live.endConfirm.failed")}</Alert>}
      </ConfirmDialog>
    </main>
  );
}

/** Time remaining (frame DemoInterview): the warning colour in the last 2 minutes, and a
 * screen-reader announcement at 5 and 1 minutes left. */
function TimeLeft({ seconds }: { seconds: number }) {
  const low = seconds <= LOW_TIME_SECONDS;
  const minutes = Math.ceil(seconds / 60);
  const [announced, setAnnounced] = useState<number | null>(null);
  const lastMinutes = useRef(minutes);

  useEffect(() => {
    const before = lastMinutes.current;
    lastMinutes.current = minutes;
    const crossed = ANNOUNCE_AT_MINUTES.find((mark) => before > mark && minutes <= mark);
    if (crossed !== undefined) setAnnounced(crossed);
  }, [minutes]);

  return (
    <>
      <span
        role="timer"
        aria-label={t("interview.live.timerLabel")}
        className={cn(
          "inline-flex h-9 shrink-0 items-center gap-2 rounded-pill px-3 md:px-3.5",
          low ? "bg-persimmon-soft text-persimmon-ink" : "bg-surface-sunk text-ink",
        )}
      >
        <ClockIcon aria-hidden="true" className="size-4" />
        <span className="hidden text-[13px] leading-4 font-semibold sm:inline">
          {t("interview.live.timeLeft")}
        </span>
        <span className="type-mono text-[15px] font-medium tabular-nums">{clock(seconds)}</span>
      </span>
      <span aria-live="assertive" className="sr-only">
        {announced !== null ? plural("interview.live.minutesLeft", announced) : ""}
      </span>
    </>
  );
}

/** The Turn, breathing while the interviewer speaks (still under reduced motion). */
function SpeakingMark({ speaking }: { speaking: boolean }) {
  const pulse = speaking
    ? "animate-[fh-turn_1.8s_ease-in-out_infinite] motion-reduce:animate-none"
    : "";
  return (
    <svg viewBox="0 0 56 56" aria-hidden="true" className="size-12 shrink-0 md:size-16">
      <path
        d="M26 4 A20 20 0 0 0 26 44 Z"
        className={cn("origin-[18px_24px] fill-evergreen", pulse)}
      />
      <path
        d="M30 14 A16 16 0 0 1 30 46 Z"
        className={cn(
          "origin-[38px_30px] fill-persimmon",
          pulse,
          speaking && "[animation-delay:0.9s]",
        )}
      />
    </svg>
  );
}

function Captions({ lines }: { lines: CaptionLine[] }) {
  const log = useRef<HTMLDivElement>(null);
  const follow = useRef(true);
  const last = lines[lines.length - 1];

  // Follow the conversation unless the candidate scrolled up to read.
  useEffect(() => {
    if (follow.current && log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [lines.length, last?.text]);

  return (
    <div className="flex flex-col bg-surface lg:min-h-0 lg:flex-1">
      <div className="flex items-baseline justify-between gap-3 px-4 pt-4 pb-2.5 md:px-8 lg:px-12">
        <h2 className="type-label text-ink-muted">{t("interview.live.captions.title")}</h2>
        <span className="hidden text-[12px] leading-4 text-ink-muted sm:inline">
          {t("interview.live.captions.hint")}
        </span>
      </div>
      <div
        ref={log}
        onScroll={(event) => {
          const element = event.currentTarget;
          follow.current = element.scrollHeight - element.scrollTop - element.clientHeight < 40;
        }}
        role="log"
        aria-live="polite"
        aria-label={t("interview.live.captions.label")}
        tabIndex={0}
        className="h-[36dvh] min-h-[180px] overflow-y-auto px-4 pb-5 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus md:px-8 lg:h-auto lg:min-h-0 lg:flex-1 lg:px-12"
      >
        {lines.length === 0 ? (
          <p className="text-[15px] leading-6 text-ink-muted">
            {t("interview.live.captions.empty")}
          </p>
        ) : (
          <ol className="flex flex-col gap-3 md:gap-4">
            {lines.map((line) => (
              <li key={line.id} className="flex flex-col gap-0.5 md:flex-row md:gap-3.5">
                <span
                  className={cn(
                    "shrink-0 text-[13px] leading-5 font-bold md:w-28 md:pt-0.5",
                    line.who === "you" ? "text-persimmon-ink" : "text-evergreen",
                  )}
                >
                  {line.who === "you"
                    ? t("interview.live.captions.you")
                    : t("interview.live.captions.ai")}
                </span>
                <span className="min-w-0 text-[15px] leading-[1.55] break-words md:text-[16px]">
                  {line.text}
                </span>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}

/** The candidate's own camera, mirrored, or a mic indicator for voice-only interviews. */
function SelfView({
  video,
  stream,
  muted,
  className,
  compact = false,
}: {
  video: boolean;
  stream: MediaStream | null;
  muted: boolean;
  className?: string;
  compact?: boolean;
}) {
  const element = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    if (element.current) element.current.srcObject = video ? stream : null;
  }, [stream, video]);

  const label = muted
    ? t("interview.live.self.micOff")
    : video
      ? t("interview.live.self.cameraOn")
      : t("interview.live.self.micOn");

  return (
    <div
      className={cn(
        "relative flex flex-col items-center justify-center gap-3 overflow-hidden rounded-md bg-on-marigold lg:rounded-lg",
        className,
      )}
    >
      {video ? (
        <video
          ref={element}
          autoPlay
          playsInline
          muted
          aria-label={t("interview.live.self.preview")}
          className="absolute inset-0 size-full -scale-x-100 object-cover"
        />
      ) : (
        <>
          {!compact && (
            <UserIcon aria-hidden="true" weight="light" className="size-14 text-marigold/70" />
          )}
          <MicBars muted={muted} compact={compact} />
        </>
      )}
      {compact ? (
        muted && (
          <span className="absolute right-1 bottom-1 flex size-6 items-center justify-center rounded-pill bg-surface-raised text-persimmon-ink">
            <MicrophoneSlashIcon aria-label={label} className="size-4" />
          </span>
        )
      ) : (
        <span className="absolute bottom-2.5 left-3 max-w-[calc(100%-24px)] truncate rounded-pill bg-surface-raised/90 px-2.5 py-1 text-[13px] leading-4 text-ink">
          {label}
        </span>
      )}
    </div>
  );
}

function MicBars({ muted, compact }: { muted: boolean; compact: boolean }) {
  const bars = useMemo(() => [0, 0.15, 0.3, 0.45, 0.6], []);
  return (
    <span aria-hidden="true" className={cn("flex items-end gap-1", compact ? "h-6" : "h-7")}>
      {bars.map((delay) => (
        <span
          key={delay}
          className={cn(
            "h-full w-[5px] origin-bottom rounded-[3px] bg-persimmon",
            muted
              ? "scale-y-[0.2] opacity-60"
              : "animate-[fh-bar_1s_ease-in-out_infinite] motion-reduce:animate-none",
          )}
          style={{ animationDelay: `${delay}s` }}
        />
      ))}
    </span>
  );
}

function Topics({ topics, current }: { topics: SessionTopic[]; current: number }) {
  return (
    <Panel title={t("interview.live.topics.title")}>
      <ol className="flex flex-col gap-3">
        {topics.map((topic) => {
          const done = topic.number < current;
          const now = topic.number === current;
          return (
            <li
              key={topic.number}
              aria-current={now ? "step" : undefined}
              className="flex items-center gap-2.5 text-[14px] leading-5"
            >
              <span
                aria-hidden="true"
                className={cn(
                  "size-2.5 shrink-0 rounded-pill",
                  done
                    ? "bg-evergreen"
                    : now
                      ? "bg-persimmon"
                      : "border-[1.5px] border-line-strong",
                )}
              />
              <span
                className={cn(now ? "font-bold text-ink" : done ? "text-ink" : "text-ink-muted")}
              >
                {topic.title}
              </span>
              {(done || now) && (
                <span className="sr-only">
                  ({done ? t("interview.live.topics.done") : t("interview.live.topics.now")})
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </Panel>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3 rounded-lg border border-line bg-surface-raised p-5">
      <h2 className="text-[15px] leading-5 font-bold">{title}</h2>
      {children}
    </section>
  );
}

function Reconnecting() {
  return (
    <div
      role="status"
      className="flex gap-3 rounded-md border border-line-strong bg-surface px-3.5 py-3"
    >
      <WifiSlashIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-ink-muted" />
      <div className="flex flex-col gap-0.5">
        <p className="text-[15px] leading-5 font-semibold">
          {t("interview.live.reconnecting.title")}
        </p>
        <p className="text-[14px] leading-5 text-ink-muted">
          {t("interview.live.reconnecting.body")}
        </p>
      </div>
    </div>
  );
}

function FailedCard({
  failure,
  video,
  onRetry,
}: {
  failure: "media" | "connect";
  video: boolean;
  onRetry: () => void;
}) {
  const media = failure === "media";
  return (
    <section
      role="alert"
      className="flex w-full max-w-[640px] flex-col gap-5 rounded-lg border border-line bg-surface-raised p-6 shadow-raised md:gap-6 md:p-10"
    >
      <span
        aria-hidden="true"
        className="flex size-12 items-center justify-center rounded-md bg-surface-sunk text-signal-gap [&_svg]:size-6"
      >
        {media ? <WarningCircleIcon /> : <WifiSlashIcon />}
      </span>
      <h1 className="type-display-lg break-words">
        {media
          ? t(
              video
                ? "interview.live.failed.mediaTitleVideo"
                : "interview.live.failed.mediaTitleVoice",
            )
          : t("interview.live.failed.connectTitle")}
      </h1>
      <p className="type-body">
        {media ? t("interview.live.failed.mediaBody") : t("interview.live.failed.connectBody")}
      </p>
      <div className="flex">
        <Button side="candidate" size="lg" onClick={onRetry} className="w-full sm:w-auto">
          {t("interview.live.failed.retry")}
        </Button>
      </div>
    </section>
  );
}

function Centred({ children }: { children: ReactNode }) {
  return (
    <main className="page-gutter flex flex-1 flex-col items-center pt-6 pb-12 md:pt-12 lg:justify-center lg:pb-18">
      {children}
    </main>
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

"use client";

import { CheckIcon, GlobeIcon, LinkIcon } from "@phosphor-icons/react";
import { type ReactNode, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/cn";
import { env } from "@/lib/env";
import { t } from "@/lib/i18n";
import { applyLink, SHARE_SOURCES, type ShareSource } from "@/lib/pipelines/wizard";

const COPIED_MS = 2500;

// Tile colours from the frame: each board gets a letter mark; careers and other get icons.
const MARKS: Record<ShareSource, { mark: ReactNode; className: string }> = {
  linkedin: { mark: "L", className: "bg-evergreen-soft text-evergreen" },
  jobstreet: { mark: "J", className: "bg-persimmon-soft text-persimmon-ink" },
  indeed: { mark: "I", className: "bg-sage text-evergreen" },
  kalibrr: { mark: "K", className: "bg-surface-sunk text-ink" },
  glassdoor: { mark: "G", className: "bg-evergreen-soft text-evergreen" },
  facebook: { mark: "F", className: "bg-persimmon-soft text-persimmon-ink" },
  careers: {
    mark: <GlobeIcon className="size-[22px]" />,
    className: "bg-surface-sunk text-evergreen",
  },
  other: {
    mark: <LinkIcon className="size-[22px]" />,
    className: "bg-surface-sunk text-ink-muted",
  },
};

/**
 * One tile per place a TA team posts the job (FR-PIPE-10). A click copies the apply link tagged
 * with that source and shows the board's posting hint. Used by the wizard's done state; PIPE-006
 * puts it in the share modal.
 */
export function ShareTiles({
  workspaceSlug,
  pipelineSlug,
  className,
}: {
  workspaceSlug: string;
  pipelineSlug: string;
  className?: string;
}) {
  const [copied, setCopied] = useState<ShareSource | null>(null);
  const [last, setLast] = useState<{ source: ShareSource; failed: boolean } | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => () => clearTimeout(timer.current), []);

  async function copy(source: ShareSource) {
    const url = applyLink(env.siteUrl, workspaceSlug, pipelineSlug, source);
    let failed = false;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      failed = true;
    }
    setLast({ source, failed });
    setCopied(failed ? null : source);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setCopied(null), COPIED_MS);
  }

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      <ul
        aria-label={t("pipelines.share.label")}
        className="grid grid-cols-2 gap-x-3 gap-y-3 sm:grid-cols-4 sm:gap-y-12"
      >
        {SHARE_SOURCES.map((source) => {
          const label = t(`pipelines.share.sources.${source}.label`);
          const on = copied === source;
          return (
            <li key={source} className="relative">
              <button
                type="button"
                onClick={() => void copy(source)}
                aria-label={t("pipelines.share.copy", { source: label })}
                className={cn(
                  "flex h-[104px] w-full flex-col items-center justify-center gap-2.5 rounded-md bg-surface-raised text-ink transition-colors hover:bg-surface",
                  on ? "border-2 border-evergreen bg-surface" : "border border-line",
                )}
              >
                <span
                  aria-hidden="true"
                  className={cn(
                    "flex size-11 items-center justify-center rounded-sm text-[18px] font-[750]",
                    MARKS[source].className,
                  )}
                >
                  {MARKS[source].mark}
                </span>
                <span className="text-[14px] leading-[18px] font-semibold">{label}</span>
              </button>
              {on && (
                <span
                  aria-hidden="true"
                  className="pointer-events-none absolute top-[calc(100%+10px)] left-1/2 z-10 hidden -translate-x-1/2 items-center gap-1.5 rounded-sm bg-ink px-3 py-1.5 text-[13px] font-semibold whitespace-nowrap text-surface-raised sm:inline-flex"
                >
                  <span className="absolute -top-[5px] left-1/2 -ml-[5px] size-2.5 rotate-45 bg-ink" />
                  <CheckIcon weight="bold" className="relative size-3.5 text-sage" />
                  <span className="relative">{t("pipelines.share.copied", { source: label })}</span>
                </span>
              )}
            </li>
          );
        })}
      </ul>
      <div role="status" className="min-h-5 text-[14px] leading-5">
        {last && !last.failed && (
          <p className="text-ink">
            <strong className="font-[650]">
              {t("pipelines.share.copied", {
                source: t(`pipelines.share.sources.${last.source}.label`),
              })}
              .
            </strong>{" "}
            <span className="text-ink-muted">
              {t(`pipelines.share.sources.${last.source}.hint`)}
            </span>
          </p>
        )}
        {last?.failed && (
          <div className="flex flex-col gap-1.5">
            <p className="text-ink-muted">{t("pipelines.share.copyFailed")}</p>
            <code className="rounded-sm bg-surface-sunk px-2 py-1.5 font-mono text-[13px] break-all text-ink select-all">
              {applyLink(env.siteUrl, workspaceSlug, pipelineSlug, last.source)}
            </code>
          </div>
        )}
      </div>
    </div>
  );
}

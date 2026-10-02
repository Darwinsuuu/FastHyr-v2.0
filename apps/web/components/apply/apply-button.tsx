"use client";

import { ArrowRightIcon, CheckIcon, EnvelopeSimpleIcon } from "@phosphor-icons/react";
import { useEffect } from "react";

import { useApplySession } from "@/components/apply/apply-session";
import { Button } from "@/components/ui/button";
import { applyDate, rememberSource, type SourceTag } from "@/lib/apply";
import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";

/**
 * Apply now, in the job header and in Role at a glance. Disabled with the reason when the pipeline
 * isn't accepting (FR-APPLY-06). Signed-out candidates sign in first, then the form opens
 * (APPLY-002); the source tag is kept for that round trip. Once the candidate has applied it
 * becomes "Applied on {date}" (APPLY-003).
 */
export function ApplyButton({
  workspaceSlug,
  pipelineSlug,
  source,
  timeZone,
  unavailable,
  size = "lg",
  showArrow = false,
  className,
  remember = false,
}: {
  workspaceSlug: string;
  pipelineSlug: string;
  source: SourceTag;
  /** The employer's time zone, for the "Applied on" date. */
  timeZone: string;
  /** Why applying is off right now, or null while the pipeline is accepting. */
  unavailable: string | null;
  size?: "md" | "lg";
  showArrow?: boolean;
  className?: string;
  /** Only one button on the page stores the tag. */
  remember?: boolean;
}) {
  const { startApply, appliedAt } = useApplySession();

  useEffect(() => {
    if (remember) rememberSource(window.sessionStorage, workspaceSlug, pipelineSlug, source);
  }, [remember, workspaceSlug, pipelineSlug, source]);

  if (appliedAt) {
    return (
      <p
        className={cn(
          "inline-flex min-h-12 items-center justify-center gap-2.5 rounded-md bg-evergreen-soft px-6 text-[15px] font-semibold text-evergreen",
          size === "lg" && "md:min-h-[54px] md:text-[16px]",
          className,
        )}
      >
        <CheckIcon aria-hidden="true" weight="bold" className="size-[18px] shrink-0" />
        {t("apply.appliedOn", { date: applyDate(appliedAt, timeZone) })}
      </p>
    );
  }

  return (
    <Button
      side="candidate"
      size={size}
      disabled={unavailable !== null}
      onClick={startApply}
      className={cn(size === "lg" && "md:min-h-[54px] md:px-7 md:text-[17px]", className)}
    >
      {t("apply.applyNow")}
      {showArrow && <ArrowRightIcon aria-hidden="true" className="size-[18px]" />}
    </Button>
  );
}

/** The line under the header's Apply now: what applying takes, why it's off, or where updates
 * go once the candidate has applied. */
export function ApplyHint({ unavailable }: { unavailable: string | null }) {
  const { candidate, appliedAt } = useApplySession();
  const hint =
    appliedAt && candidate
      ? t("apply.appliedHint", { email: candidate.email })
      : (unavailable ?? (candidate ? t("apply.applyHintSignedIn") : t("apply.applyHint")));
  return <p className="text-[13px] leading-5 break-words text-ink-muted lg:text-right">{hint}</p>;
}

/** "Your application is in" at the top of the page once the candidate has applied (FR-APPLY-07:
 * status text only). */
export function AppliedNotice() {
  const { appliedAt } = useApplySession();
  if (!appliedAt) return null;
  return (
    <div
      role="status"
      className="flex gap-3.5 rounded-[16px] border border-evergreen/25 bg-evergreen-soft/60 p-4 md:px-5 md:py-[18px]"
    >
      <span
        aria-hidden="true"
        className="flex size-9 shrink-0 items-center justify-center rounded-[10px] bg-evergreen text-on-evergreen"
      >
        <EnvelopeSimpleIcon className="size-[18px]" />
      </span>
      <span className="flex flex-col gap-1">
        <strong className="text-[15px] leading-[21px]">{t("apply.appliedTitle")}</strong>
        <span className="text-[14px] leading-[22px] text-ink/85">{t("apply.appliedBody")}</span>
      </span>
    </div>
  );
}

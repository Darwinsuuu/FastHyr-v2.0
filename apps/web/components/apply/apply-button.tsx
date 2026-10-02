"use client";

import {
  ArrowRightIcon,
  CheckIcon,
  EnvelopeSimpleIcon,
  UsersThreeIcon,
  VideoCameraIcon,
} from "@phosphor-icons/react";
import { useEffect } from "react";

import { useApplySession } from "@/components/apply/apply-session";
import { Button } from "@/components/ui/button";
import { applyDate, appliedStatusText, rememberSource, type SourceTag } from "@/lib/apply";
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

const STATUS_ICON = {
  received: EnvelopeSimpleIcon,
  interview: VideoCameraIcon,
  with_team: UsersThreeIcon,
} as const;

/** "Your application is in" at the top of the page once the candidate has applied, then where it
 * is in candidate-safe words (FR-APPLY-05, FR-APPLY-07: status text only, never a decision). */
export function AppliedNotice({ company }: { company: string }) {
  const { candidate, appliedAt, status } = useApplySession();
  if (!appliedAt || !candidate) return null;
  const { title, body } = appliedStatusText(status ?? "received", {
    company,
    email: candidate.email,
  });
  const StatusIcon = STATUS_ICON[status ?? "received"];
  return (
    <div
      role="status"
      className="flex gap-3.5 rounded-[16px] border border-evergreen/25 bg-evergreen-soft/60 p-4 md:px-5 md:py-[18px]"
    >
      <span
        aria-hidden="true"
        className="flex size-9 shrink-0 items-center justify-center rounded-[10px] bg-evergreen text-on-evergreen"
      >
        <StatusIcon className="size-[18px]" />
      </span>
      <span className="flex min-w-0 flex-col gap-1">
        <strong className="text-[15px] leading-[21px]">{title}</strong>
        <span className="text-[14px] leading-[22px] break-words text-ink/85">{body}</span>
      </span>
    </div>
  );
}

"use client";

import { ArrowRightIcon } from "@phosphor-icons/react";
import { useEffect } from "react";

import { useApplySession } from "@/components/apply/apply-session";
import { Button } from "@/components/ui/button";
import { rememberSource, type SourceTag } from "@/lib/apply";
import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";

/**
 * Apply now, in the job header and in Role at a glance. Disabled with the reason when the pipeline
 * isn't accepting (FR-APPLY-06). Signed-out candidates sign in first, then the form opens
 * (APPLY-002); the source tag is kept for that round trip.
 */
export function ApplyButton({
  workspaceSlug,
  pipelineSlug,
  source,
  unavailable,
  size = "lg",
  showArrow = false,
  className,
  remember = false,
}: {
  workspaceSlug: string;
  pipelineSlug: string;
  source: SourceTag;
  /** Why applying is off right now, or null while the pipeline is accepting. */
  unavailable: string | null;
  size?: "md" | "lg";
  showArrow?: boolean;
  className?: string;
  /** Only one button on the page stores the tag. */
  remember?: boolean;
}) {
  const { startApply } = useApplySession();

  useEffect(() => {
    if (remember) rememberSource(window.sessionStorage, workspaceSlug, pipelineSlug, source);
  }, [remember, workspaceSlug, pipelineSlug, source]);

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

/** The line under the header's Apply now: what applying takes, or why it's off. */
export function ApplyHint({ unavailable }: { unavailable: string | null }) {
  const { candidate } = useApplySession();
  return (
    <p className="text-[13px] leading-5 text-ink-muted lg:text-right">
      {unavailable ?? (candidate ? t("apply.applyHintSignedIn") : t("apply.applyHint"))}
    </p>
  );
}

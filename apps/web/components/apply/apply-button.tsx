"use client";

import { ArrowRightIcon } from "@phosphor-icons/react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { rememberSource, type SourceTag } from "@/lib/apply";
import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";

/**
 * Apply now, in the job header and in Role at a glance. Disabled with the reason when the pipeline
 * isn't accepting (FR-APPLY-06). Keeps the source tag for the sign-in round trip (APPLY-002).
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
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (remember) rememberSource(window.sessionStorage, workspaceSlug, pipelineSlug, source);
  }, [remember, workspaceSlug, pipelineSlug, source]);

  return (
    <>
      <Button
        side="candidate"
        size={size}
        disabled={unavailable !== null}
        onClick={() => setOpen(true)}
        className={cn(size === "lg" && "md:min-h-[54px] md:px-7 md:text-[17px]", className)}
      >
        {t("apply.applyNow")}
        {showArrow && <ArrowRightIcon aria-hidden="true" className="size-[18px]" />}
      </Button>
      {/* Candidate sign-in and the application form come with APPLY-002 and APPLY-003. */}
      <Dialog
        open={open}
        onOpenChange={setOpen}
        size="sm"
        title={t("apply.soon.title")}
        description={t("apply.soon.body")}
        footer={
          <Button side="candidate" onClick={() => setOpen(false)}>
            {t("apply.soon.close")}
          </Button>
        }
      />
    </>
  );
}

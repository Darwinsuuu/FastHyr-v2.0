"use client";

import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import type { PublicPipeline } from "@/lib/apply";
import type { Candidate } from "@/lib/apply/session";
import { t } from "@/lib/i18n";

/**
 * The application modal (frame Apply): the role, and the account the application goes under.
 * The form itself (résumé, contact details, consent) is APPLY-003.
 */
export function ApplicationDialog({
  open,
  onOpenChange,
  pipeline,
  candidate,
  onNotYou,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  pipeline: PublicPipeline;
  candidate: Candidate;
  /** Signs out and asks for the right account. */
  onNotYou: () => void;
}) {
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      size="lg"
      title={
        <span className="flex flex-col gap-1">
          <span className="text-[13px] leading-5 font-normal tracking-normal text-ink-muted">
            {t("apply.form.applyingTo", { company: pipeline.company.name })}
          </span>
          <span className="font-display text-[24px] leading-[30px] font-[560] md:text-[26px] md:leading-8">
            {pipeline.title}
          </span>
        </span>
      }
      footer={
        <Button side="candidate" onClick={() => onOpenChange(false)}>
          {t("apply.form.close")}
        </Button>
      }
    >
      <div className="flex flex-col gap-5">
        <div className="flex items-center gap-3 rounded-md bg-surface px-3.5 py-3">
          <Avatar id={candidate.id} name={candidate.name} />
          <span className="flex min-w-0 flex-1 flex-col">
            <span className="truncate text-[14px] leading-5 font-semibold">{candidate.email}</span>
            <span className="text-[12px] leading-4 text-ink-muted">
              {t("apply.form.signedInAs", {
                provider: t(`auth.provider.${candidate.provider}`),
              })}
            </span>
          </span>
          <button
            type="button"
            onClick={onNotYou}
            className="min-h-11 shrink-0 px-1 text-[13px] font-semibold text-persimmon-ink hover:underline md:min-h-0"
          >
            {t("apply.form.notYou")}
          </button>
        </div>
        {/* APPLY-003 replaces this with the application form. */}
        <div className="flex flex-col gap-1.5">
          <h3 className="text-[16px] leading-6 font-semibold">{t("apply.form.soonTitle")}</h3>
          <p className="text-[15px] leading-6 text-ink-muted">{t("apply.form.soonBody")}</p>
        </div>
      </div>
    </Dialog>
  );
}

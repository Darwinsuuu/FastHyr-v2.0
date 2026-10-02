"use client";

import { CheckIcon } from "@phosphor-icons/react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import type { PublicPipeline } from "@/lib/apply";
import { firstName } from "@/lib/apply/form";
import { t } from "@/lib/i18n";

/** "Application sent" with what happens next (frame Apply, FR-APPLY-04). */
export function SentDialog({
  open,
  onOpenChange,
  pipeline,
  fullName,
  email,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  pipeline: PublicPipeline;
  fullName: string;
  email: string;
}) {
  const name = firstName(fullName);
  const steps = [
    t("apply.sent.step1"),
    t("apply.sent.step2", { email }),
    t("apply.sent.step3", { company: pipeline.company.name }),
  ];
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      size="sm"
      leading={
        <span
          aria-hidden="true"
          className="flex size-12 shrink-0 items-center justify-center rounded-pill bg-evergreen-soft text-evergreen md:size-14"
        >
          <CheckIcon weight="bold" className="size-6" />
        </span>
      }
      title={
        <span className="font-display text-[26px] leading-8 font-[560]">
          {t("apply.sent.title")}
        </span>
      }
      description={
        name
          ? t("apply.sent.body", { name, title: pipeline.title, company: pipeline.company.name })
          : t("apply.sent.bodyNoName", { title: pipeline.title, company: pipeline.company.name })
      }
      footer={<Button onClick={() => onOpenChange(false)}>{t("apply.sent.done")}</Button>}
    >
      <div className="flex flex-col gap-3 rounded-[14px] bg-surface p-4 md:px-[18px]">
        <h3 className="type-label text-ink-muted">{t("apply.sent.nextTitle")}</h3>
        <ol className="flex flex-col gap-3">
          {steps.map((step, index) => (
            <li
              key={step}
              className="grid grid-cols-[24px_minmax(0,1fr)] gap-2.5 text-[14px] leading-[21px] break-words"
            >
              <span
                aria-hidden="true"
                className="flex size-[22px] items-center justify-center rounded-pill border border-line-strong bg-surface-raised font-mono text-[11px] text-evergreen"
              >
                {index + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>
      </div>
    </Dialog>
  );
}

"use client";

import { ArrowSquareOutIcon } from "@phosphor-icons/react";
import Link from "next/link";

import type { StepProps } from "@/components/pipelines/wizard-role-step";
import { Field } from "@/components/ui/field";
import { Slider } from "@/components/ui/slider";
import { Toggle } from "@/components/ui/toggle";
import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";
import { PASS_MARK_MAX, PASS_MARK_MIN, WEIGHTS, weightsTotal } from "@/lib/pipelines/wizard";

/** Step 3, Scoring (frame NewPipeline step 3, FR-PIPE-03). */
export function ScoringStep({ form, update, tried }: StepProps) {
  const total = weightsTotal(form);
  const sumOk = total === 100;
  return (
    <div className="flex flex-col gap-7">
      <section
        aria-labelledby="rubric-heading"
        className="flex flex-col gap-4 rounded-md border border-line p-4 md:p-5"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 id="rubric-heading" className="text-[15px] leading-5 font-[650] text-ink">
            {t("pipelines.wizard.scoring.rubric")}
          </h3>
          <span
            role="status"
            className={cn(
              "inline-flex min-h-7 items-center rounded-sm px-2.5 text-[13px] font-bold",
              sumOk ? "bg-evergreen-soft text-evergreen" : "bg-persimmon-soft text-persimmon-ink",
              !sumOk && tried && "ring-2 ring-signal-gap",
            )}
          >
            {sumOk
              ? t("pipelines.wizard.scoring.sumOk")
              : t("pipelines.wizard.scoring.sumOff", { total })}
          </span>
        </div>
        {WEIGHTS.map((key) => (
          <Field
            key={key}
            className="gap-0 sm:grid sm:grid-cols-[180px_minmax(0,1fr)_56px] sm:items-center sm:gap-4"
            label={
              <span className="flex items-center justify-between gap-3 font-normal sm:contents">
                <span>{t(`pipelines.wizard.scoring.weights.${key}`)}</span>
                <span className="font-mono text-[14px] text-evergreen tabular-nums sm:hidden">
                  {t("pipelines.wizard.scoring.percent", { value: form[key] })}
                </span>
              </span>
            }
          >
            <Slider
              aria-label={t(`pipelines.wizard.scoring.weights.${key}`)}
              value={form[key]}
              min={0}
              max={100}
              step={5}
              formatValue={(value) => t("pipelines.wizard.scoring.percent", { value })}
              onValueChange={(value) => update({ [key]: value })}
            />
            <span
              aria-hidden="true"
              className="hidden text-right font-mono text-[14px] text-evergreen tabular-nums sm:block"
            >
              {t("pipelines.wizard.scoring.percent", { value: form[key] })}
            </span>
          </Field>
        ))}
        <p className="text-[13px] leading-[18px] text-ink-muted">
          {t("pipelines.wizard.scoring.rubricHint")}
        </p>
      </section>

      <Field
        label={
          <span className="flex items-center justify-between gap-3">
            <span>{t("pipelines.wizard.scoring.passMark")}</span>
            <span className="text-[15px] font-semibold text-ink tabular-nums">
              {t("pipelines.wizard.scoring.passMarkValue", { value: form.pass_mark })}
            </span>
          </span>
        }
        hint={t("pipelines.wizard.scoring.passMarkHint")}
      >
        <Slider
          aria-label={t("pipelines.wizard.scoring.passMark")}
          value={form.pass_mark}
          min={PASS_MARK_MIN}
          max={PASS_MARK_MAX}
          step={5}
          formatValue={(value) => t("pipelines.wizard.scoring.passMarkValue", { value })}
          onValueChange={(pass_mark) => update({ pass_mark })}
        />
      </Field>

      <section className="flex flex-col gap-3 rounded-md border border-line p-4 md:p-5">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-[15px] leading-5 font-[650] text-ink">
            {t("pipelines.wizard.scoring.messages")}
          </h3>
          {/* A new tab, so the wizard's unsaved steps stay as they are. */}
          <Link
            href="/settings/email-templates"
            target="_blank"
            className="inline-flex min-h-11 items-center gap-1.5 text-[13px] font-semibold text-evergreen md:min-h-0"
          >
            {t("pipelines.wizard.scoring.editTemplates")}
            <ArrowSquareOutIcon aria-hidden="true" className="size-4" />
          </Link>
        </div>
        <div className="flex flex-col divide-y divide-line">
          <Toggle
            label={t("pipelines.wizard.scoring.rejectMail")}
            description={t("pipelines.wizard.scoring.rejectMailHint")}
            checked={form.email_resume_reject}
            onCheckedChange={(email_resume_reject) => update({ email_resume_reject })}
          />
          <Toggle
            label={t("pipelines.wizard.scoring.resultMail")}
            description={t("pipelines.wizard.scoring.resultMailHint")}
            checked={form.email_post_interview}
            onCheckedChange={(email_post_interview) => update({ email_post_interview })}
          />
        </div>
      </section>
    </div>
  );
}

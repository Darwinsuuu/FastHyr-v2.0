"use client";

import { InfoIcon } from "@phosphor-icons/react";

import type { StepProps } from "@/components/pipelines/wizard-role-step";
import { WizardNote } from "@/components/pipelines/wizard-note";
import { ChoiceCards } from "@/components/ui/choice-cards";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { NumberStepper } from "@/components/ui/number-stepper";
import { SegmentedControl } from "@/components/ui/segmented-control";
import { cn } from "@/lib/cn";
import { formatDayLong, formatNumber } from "@/lib/format";
import { t } from "@/lib/i18n";
import {
  closeDate,
  type DurationDays,
  DURATIONS,
  firstOpeningDay,
  OPEN_MODES,
  RESERVE_MIN,
  RESERVE_STEP,
} from "@/lib/pipelines/wizard";

const EXPLAINERS = ["perApplicant", "pauses", "returns"] as const;

function GroupLabel({ children }: { children: string }) {
  return <span className="text-[14px] leading-5 font-semibold text-ink">{children}</span>;
}

export interface ScheduleStepProps extends StepProps {
  /** The workspace's free credits, null while loading. */
  freeCredits: number | null;
  /**
   * A scheduled pipeline being edited: its open mode and reserve are fixed (Start now and
   * top-up change them), so they show read only. `reserved` is what it holds.
   */
  scheduled?: { reserved: number };
}

/** Step 4, Schedule & credits (frame NewPipeline step 4, FR-PIPE-04). */
export function ScheduleStep({ form, update, tried, freeCredits, scheduled }: ScheduleStepProps) {
  const isLater = form.open_mode === "scheduled";
  const minDay = firstOpeningDay();
  const dateMissing = isLater && (!form.opens_on || form.opens_on < minDay);
  const over = !scheduled && freeCredits !== null && form.credits_to_reserve > freeCredits;
  const ratio =
    freeCredits && freeCredits > 0 ? Math.min(1, form.credits_to_reserve / freeCredits) : 1;

  return (
    <div className="flex flex-col gap-7">
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-1.5">
          <GroupLabel>{t("pipelines.wizard.schedule.when")}</GroupLabel>
          {scheduled ? (
            <WizardNote icon={<InfoIcon aria-hidden="true" />}>
              <strong className="font-[650]">
                {t("pipelines.wizard.schedule.modes.scheduled.label")}.
              </strong>{" "}
              {t("pipelines.wizard.schedule.modeLocked")}
            </WizardNote>
          ) : (
            <ChoiceCards
              label={t("pipelines.wizard.schedule.when")}
              options={OPEN_MODES.map((value) => ({
                value,
                label: t(`pipelines.wizard.schedule.modes.${value}.label`),
                description: t(`pipelines.wizard.schedule.modes.${value}.description`),
              }))}
              value={form.open_mode}
              onValueChange={(open_mode) =>
                update({ open_mode, opens_on: form.opens_on || minDay })
              }
            />
          )}
        </div>
        {isLater && (
          <Field
            label={t("pipelines.wizard.schedule.openingDate")}
            error={tried && dateMissing ? t("pipelines.wizard.blocked.openingDate") : undefined}
            className="sm:max-w-[280px]"
          >
            <Input
              type="date"
              min={minDay}
              value={form.opens_on}
              onChange={(event) => update({ opens_on: event.target.value })}
            />
          </Field>
        )}
      </div>

      <div className="flex flex-col gap-2.5">
        <GroupLabel>{t("pipelines.wizard.schedule.duration")}</GroupLabel>
        <SegmentedControl
          label={t("pipelines.wizard.schedule.duration")}
          options={DURATIONS.map((days) => ({
            value: String(days),
            label: t("pipelines.wizard.schedule.durationDays", { days }),
          }))}
          value={String(form.duration_days)}
          onValueChange={(value) => update({ duration_days: Number(value) as DurationDays })}
          fullWidth
          className="sm:max-w-[520px]"
        />
        <p className="text-[14px] leading-5 text-ink">
          {t("pipelines.wizard.schedule.closesOn", { date: formatDayLong(closeDate(form)) })}{" "}
          <span className="text-ink-muted">{t("pipelines.wizard.schedule.noExtend")}</span>
        </p>
      </div>

      <section
        aria-labelledby="reserve-heading"
        className="flex flex-col gap-4 rounded-md border border-line p-4 md:p-5"
      >
        <div className="flex flex-col gap-0.5">
          <h3 id="reserve-heading" className="text-[15px] leading-5 font-[650] text-ink">
            {t("pipelines.wizard.schedule.reserve")}
          </h3>
          <p className="text-[13px] leading-[19px] text-ink-muted">
            {t("pipelines.wizard.schedule.reserveHint")}
          </p>
        </div>
        {scheduled ? (
          <p className="text-[14px] leading-5 text-ink">
            {t("pipelines.wizard.schedule.reserveLocked", {
              credits: formatNumber(scheduled.reserved),
            })}
          </p>
        ) : (
          <>
            <Field
              label={t("pipelines.wizard.schedule.reserveLabel")}
              hideLabel
              error={over && tried ? t("pipelines.wizard.blocked.credits") : undefined}
            >
              <div className="flex items-center gap-3">
                <NumberStepper
                  value={form.credits_to_reserve}
                  min={RESERVE_MIN}
                  step={RESERVE_STEP}
                  unit={t("pipelines.wizard.schedule.creditsUnit")}
                  onValueChange={(value) =>
                    update({
                      credits_to_reserve: Math.max(
                        RESERVE_MIN,
                        Math.round(value / RESERVE_STEP) * RESERVE_STEP,
                      ),
                    })
                  }
                />
                <span className="text-[14px] text-ink-muted">
                  {t("pipelines.wizard.schedule.creditsUnit")}
                </span>
              </div>
            </Field>
            {freeCredits !== null && (
              <div className="flex flex-col gap-1.5">
                <div
                  aria-hidden="true"
                  className="h-2 overflow-hidden rounded-pill bg-surface-sunk"
                >
                  <div
                    className={cn("h-2 rounded-pill", over ? "bg-signal-gap" : "bg-evergreen")}
                    style={{ width: `${Math.round(ratio * 100)}%` }}
                  />
                </div>
                <p
                  role="status"
                  className={cn(
                    "text-[13px] leading-[18px]",
                    over ? "font-semibold text-signal-gap" : "text-ink-muted",
                  )}
                >
                  {over
                    ? t("pipelines.wizard.schedule.reserveOver", {
                        free: formatNumber(freeCredits),
                      })
                    : t("pipelines.wizard.schedule.reserveNote", {
                        credits: formatNumber(form.credits_to_reserve),
                        left: formatNumber(freeCredits - form.credits_to_reserve),
                      })}
                </p>
              </div>
            )}
          </>
        )}
        <div className="grid gap-3 border-t border-line pt-3.5 sm:grid-cols-3">
          {EXPLAINERS.map((key) => (
            <div key={key} className="flex flex-col gap-1">
              <span className="text-[13px] font-[650] text-ink">
                {t(`pipelines.wizard.schedule.explainers.${key}.title`)}
              </span>
              <span className="text-[13px] leading-[18px] text-ink-muted">
                {t(`pipelines.wizard.schedule.explainers.${key}.body`)}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

"use client";

import { CheckIcon } from "@phosphor-icons/react";

import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";

export interface Step {
  label: string;
  /** One line under the label, e.g. "Job details and must-haves". */
  hint?: string;
}

export interface StepperProps {
  steps: Step[];
  /** 0-based index of the current step. */
  current: number;
  /** Lets people jump back to a done step (the wizard). */
  onStepClick?: (index: number) => void;
  /** vertical: the wizard's side nav. horizontal: the demo's step bars. */
  orientation?: "vertical" | "horizontal";
  /** Names the list for screen readers, e.g. "New pipeline steps". */
  label: string;
  className?: string;
}

type State = "done" | "current" | "upcoming";

const stateOf = (index: number, current: number): State =>
  index < current ? "done" : index === current ? "current" : "upcoming";

/** Phones: "Step 2 of 5" with the step name and a progress bar (RESPONSIVE.md). */
function CompactStepper({
  steps,
  current,
  className,
}: Pick<StepperProps, "steps" | "current" | "className">) {
  const step = steps[current];
  return (
    <div className={className}>
      <div className="flex items-baseline justify-between gap-3">
        <span className="type-label text-ink-muted">
          {t("ui.stepOf", { step: current + 1, total: steps.length })}
        </span>
        {step && <span className="truncate text-[15px] font-[650] text-ink">{step.label}</span>}
      </div>
      <div
        role="progressbar"
        aria-label={t("ui.stepOf", { step: current + 1, total: steps.length })}
        aria-valuemin={1}
        aria-valuemax={steps.length}
        aria-valuenow={current + 1}
        className="mt-2 h-1 overflow-hidden rounded-pill bg-line"
      >
        <div
          className="h-full rounded-pill bg-evergreen transition-[width] duration-300 ease-out"
          style={{ width: `${((current + 1) / steps.length) * 100}%` }}
        />
      </div>
    </div>
  );
}

/** Wizard and demo progress. The full stepper shows from md; phones get the compact header. */
export function Stepper({
  steps,
  current,
  onStepClick,
  orientation = "vertical",
  label,
  className,
}: StepperProps) {
  if (orientation === "horizontal") {
    return (
      <div className={className}>
        <CompactStepper steps={steps} current={current} className="md:hidden" />
        <ol
          aria-label={label}
          className="hidden gap-2 md:grid"
          style={{ gridTemplateColumns: `repeat(${steps.length}, 1fr)` }}
        >
          {steps.map((step, index) => {
            const state = stateOf(index, current);
            return (
              <li
                key={step.label}
                aria-current={state === "current" ? "step" : undefined}
                className="flex flex-col gap-2.5"
              >
                <span
                  className={cn(
                    "h-1 rounded-pill",
                    state === "upcoming" ? "bg-line" : "bg-evergreen",
                  )}
                />
                <span className="flex items-center gap-2">
                  <span
                    className={cn(
                      "flex size-[22px] shrink-0 items-center justify-center rounded-pill text-[12px] font-bold",
                      state === "upcoming"
                        ? "bg-surface-sunk text-ink-muted"
                        : "bg-evergreen text-on-evergreen",
                    )}
                  >
                    {state === "done" ? (
                      <CheckIcon weight="bold" className="size-3" aria-label={t("ui.completed")} />
                    ) : (
                      index + 1
                    )}
                  </span>
                  <span
                    className={cn(
                      "text-[15px] text-ink",
                      state === "current" ? "font-bold" : "font-semibold",
                    )}
                  >
                    {step.label}
                  </span>
                </span>
                {step.hint && (
                  <span className="pl-[30px] text-[13px] text-ink-muted">{step.hint}</span>
                )}
              </li>
            );
          })}
        </ol>
      </div>
    );
  }

  return (
    <div className={className}>
      <CompactStepper steps={steps} current={current} className="md:hidden" />
      <ol aria-label={label} className="hidden flex-col gap-1 md:flex">
        {steps.map((step, index) => {
          const state = stateOf(index, current);
          const clickable = Boolean(onStepClick) && state === "done";
          const content = (
            <>
              <span
                className={cn(
                  "flex size-[30px] shrink-0 items-center justify-center rounded-pill border-[1.5px] text-[13px] font-bold",
                  state === "done" && "border-evergreen bg-evergreen text-on-evergreen",
                  state === "current" && "border-evergreen bg-surface-raised text-evergreen",
                  state === "upcoming" && "border-line-strong text-ink-muted",
                )}
              >
                {state === "done" ? (
                  <CheckIcon weight="bold" className="size-3.5" aria-label={t("ui.completed")} />
                ) : (
                  index + 1
                )}
              </span>
              <span className="flex flex-col text-left">
                <span
                  className={cn(
                    "text-[15px] leading-5 font-[650]",
                    state === "upcoming" ? "text-ink-muted" : "text-ink",
                  )}
                >
                  {step.label}
                </span>
                {step.hint && (
                  <span className="text-[13px] leading-[18px] text-ink-muted">{step.hint}</span>
                )}
              </span>
            </>
          );
          const rowClasses = cn(
            "flex w-full items-center gap-3.5 rounded-[12px] p-3",
            state === "current" && "bg-surface-raised",
          );
          return (
            <li key={step.label} aria-current={state === "current" ? "step" : undefined}>
              {clickable ? (
                <button
                  type="button"
                  onClick={() => onStepClick?.(index)}
                  className={cn(rowClasses, "hover:bg-surface-raised")}
                >
                  {content}
                </button>
              ) : (
                <div className={rowClasses}>{content}</div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

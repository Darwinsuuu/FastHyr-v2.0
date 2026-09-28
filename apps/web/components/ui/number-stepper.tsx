"use client";

import { MinusIcon, PlusIcon } from "@phosphor-icons/react";
import { useState } from "react";

import { useFieldControl } from "@/components/ui/field";
import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";

export interface NumberStepperProps {
  value?: number;
  defaultValue?: number;
  onValueChange?: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  /** Names the buttons for screen readers, e.g. "credits" → "Add 10 credits". */
  unit?: string;
  className?: string;
}

export function clampToRange(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/** − value + for counts such as credits; typing works too and is clamped to min/max. */
export function NumberStepper({
  value,
  defaultValue = 0,
  onValueChange,
  min = 0,
  max = Number.MAX_SAFE_INTEGER,
  step = 1,
  disabled,
  unit,
  className,
}: NumberStepperProps) {
  const field = useFieldControl();
  const [internal, setInternal] = useState(defaultValue);
  const current = value ?? internal;
  const [draft, setDraft] = useState<string | null>(null);

  function commit(next: number) {
    const clamped = clampToRange(Number.isFinite(next) ? next : current, min, max);
    if (value === undefined) setInternal(clamped);
    onValueChange?.(clamped);
    setDraft(null);
  }

  const buttonClasses =
    "flex size-11 shrink-0 items-center justify-center text-ink transition-colors hover:bg-surface-sunk disabled:cursor-not-allowed disabled:opacity-40";

  return (
    <div
      className={cn(
        "inline-flex h-12 items-stretch overflow-hidden rounded-sm border border-line-strong bg-surface-raised",
        "has-aria-invalid:border-signal-gap",
        className,
      )}
    >
      <button
        type="button"
        aria-label={unit ? t("ui.removeAmount", { amount: step, unit }) : t("ui.decrease")}
        className={buttonClasses}
        disabled={disabled || current <= min}
        onClick={() => commit(current - step)}
      >
        <MinusIcon aria-hidden="true" className="size-5" />
      </button>
      <input
        {...field}
        type="text"
        inputMode="numeric"
        disabled={disabled}
        value={draft ?? String(current)}
        onChange={(event) => setDraft(event.target.value.replace(/[^\d-]/g, ""))}
        onBlur={() => draft !== null && commit(Number.parseInt(draft, 10))}
        onKeyDown={(event) => {
          if (event.key === "Enter" && draft !== null) commit(Number.parseInt(draft, 10));
          if (event.key === "ArrowUp") commit(current + step);
          if (event.key === "ArrowDown") commit(current - step);
        }}
        className="w-16 border-x border-line bg-transparent text-center text-base font-semibold text-ink tabular-nums md:text-[15px]"
      />
      <button
        type="button"
        aria-label={unit ? t("ui.addAmount", { amount: step, unit }) : t("ui.increase")}
        className={buttonClasses}
        disabled={disabled || current >= max}
        onClick={() => commit(current + step)}
      >
        <PlusIcon aria-hidden="true" className="size-5" />
      </button>
    </div>
  );
}

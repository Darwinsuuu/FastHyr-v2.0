"use client";

import { createContext, type ReactNode, useContext, useId } from "react";

import { cn } from "@/lib/cn";

interface FieldContextValue {
  id: string;
  describedBy: string | undefined;
  invalid: boolean;
  required: boolean;
}

const FieldContext = createContext<FieldContextValue | null>(null);

/** Props a control inside a Field spreads onto its input so the label, hint and error are read. */
export function useFieldControl(): {
  id?: string;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean;
  required?: boolean;
} {
  const field = useContext(FieldContext);
  if (!field) return {};
  return {
    id: field.id,
    "aria-describedby": field.describedBy,
    "aria-invalid": field.invalid || undefined,
    required: field.required || undefined,
  };
}

export interface FieldProps {
  label: ReactNode;
  /** Help under the control, e.g. "The change takes effect immediately." */
  hint?: ReactNode;
  /** Replaces nothing: shown under the hint in signal-gap, and marks the control invalid. */
  error?: ReactNode;
  required?: boolean;
  /** Visually hide the label (it stays for screen readers), e.g. a search box with a placeholder. */
  hideLabel?: boolean;
  className?: string;
  children: ReactNode;
}

/** Label + control + hint + error, wired for screen readers (label/hint/error pattern from frames). */
export function Field({
  label,
  hint,
  error,
  required = false,
  hideLabel,
  className,
  children,
}: FieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <FieldContext.Provider value={{ id, describedBy, invalid: Boolean(error), required }}>
      <div className={cn("flex flex-col gap-1.5", className)}>
        <label
          htmlFor={id}
          className={cn("text-[14px] leading-5 font-semibold text-ink", hideLabel && "sr-only")}
        >
          {label}
        </label>
        {children}
        {hint && (
          <p id={hintId} className="text-[13px] leading-[18px] text-ink-muted">
            {hint}
          </p>
        )}
        {error && (
          <p
            id={errorId}
            role="alert"
            className="text-[13px] leading-[18px] font-semibold text-signal-gap"
          >
            {error}
          </p>
        )}
      </div>
    </FieldContext.Provider>
  );
}

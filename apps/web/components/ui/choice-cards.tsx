"use client";

import { type KeyboardEvent, type ReactNode, useRef } from "react";

import { cn } from "@/lib/cn";

export interface ChoiceCardOption<T extends string> {
  value: T;
  label: string;
  description?: string;
  /** A 20 px Phosphor icon in a rounded tile (interview format). */
  icon?: ReactNode;
}

export interface ChoiceCardsProps<T extends string> {
  options: ChoiceCardOption<T>[];
  value: T;
  onValueChange: (value: T) => void;
  /** Names the group for screen readers, e.g. "Interview format". */
  label: string;
  /** Grid columns from `sm`; phones always stack. */
  columns?: 2 | 3;
  className?: string;
}

const COLUMNS = { 2: "sm:grid-cols-2", 3: "sm:grid-cols-3" } as const;

/** Mutually exclusive options with a description each (interview format, tone). A radio group. */
export function ChoiceCards<T extends string>({
  options,
  value,
  onValueChange,
  label,
  columns = 2,
  className,
}: ChoiceCardsProps<T>) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function onKeyDown(event: KeyboardEvent, index: number) {
    const delta = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
    if (!delta) return;
    event.preventDefault();
    const next = (index + delta + options.length) % options.length;
    const option = options[next];
    if (!option) return;
    onValueChange(option.value);
    refs.current[next]?.focus();
  }

  return (
    <div
      role="radiogroup"
      aria-label={label}
      className={cn("grid gap-3", COLUMNS[columns], className)}
    >
      {options.map((option, index) => {
        const selected = option.value === value;
        return (
          <button
            key={option.value}
            ref={(element) => {
              refs.current[index] = element;
            }}
            type="button"
            role="radio"
            aria-checked={selected}
            tabIndex={selected ? 0 : -1}
            onClick={() => onValueChange(option.value)}
            onKeyDown={(event) => onKeyDown(event, index)}
            className={cn(
              "flex items-start gap-3 rounded-md border p-4 text-left transition-colors duration-200 ease-out",
              selected
                ? "border-evergreen bg-surface ring-1 ring-evergreen"
                : "border-line bg-surface-raised hover:border-line-strong",
            )}
          >
            {option.icon && (
              <span
                aria-hidden="true"
                className={cn(
                  "flex size-10 shrink-0 items-center justify-center rounded-[10px] text-evergreen [&>svg]:size-5",
                  selected ? "bg-evergreen-soft" : "bg-surface-sunk",
                )}
              >
                {option.icon}
              </span>
            )}
            <span className="flex flex-col gap-1">
              <span className="text-[15px] leading-5 font-[650] text-ink">{option.label}</span>
              {option.description && (
                <span className="text-[13px] leading-[18px] text-ink-muted">
                  {option.description}
                </span>
              )}
            </span>
          </button>
        );
      })}
    </div>
  );
}

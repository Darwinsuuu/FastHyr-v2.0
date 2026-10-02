"use client";

import { type KeyboardEvent, useRef } from "react";

import { cn } from "@/lib/cn";

export interface SegmentedOption<T extends string> {
  value: T;
  label: string;
}

export interface SegmentedControlProps<T extends string> {
  options: SegmentedOption<T>[];
  value: T;
  onValueChange: (value: T) => void;
  /** Names the group for screen readers, e.g. "Time range". */
  label: string;
  size?: "sm" | "md";
  /** Stretch segments to fill the width (useful on phones). */
  fullWidth?: boolean;
  className?: string;
}

/** A small set of mutually exclusive options (week / 30 days, work setup). A radio group underneath. */
export function SegmentedControl<T extends string>({
  options,
  value,
  onValueChange,
  label,
  size = "md",
  fullWidth,
  className,
}: SegmentedControlProps<T>) {
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
      className={cn(
        "inline-flex max-w-full gap-1 overflow-x-auto rounded-md bg-surface-sunk p-1",
        fullWidth && "flex w-full",
        className,
      )}
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
              "rounded-[9px] font-semibold whitespace-nowrap transition-colors duration-200 ease-out",
              size === "md" ? "min-h-10 text-[14px]" : "min-h-8 text-[13px]",
              // Full width: segments share the row and tighten on phones before scrolling.
              fullWidth ? "min-w-0 flex-1 px-2 sm:px-3.5" : "shrink-0 px-3.5",
              selected
                ? "bg-surface-raised text-ink shadow-[0_1px_2px_rgba(30,42,38,0.12)]"
                : "text-ink-muted hover:text-ink",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

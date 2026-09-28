"use client";

import { XIcon } from "@phosphor-icons/react";
import { type KeyboardEvent, useState } from "react";

import { useFieldControl } from "@/components/ui/field";
import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";

export interface ChipInputProps {
  value: string[];
  onValueChange: (value: string[]) => void;
  placeholder?: string;
  /** Stops adding once reached. */
  max?: number;
  disabled?: boolean;
  className?: string;
}

/** Free-text chips (must-haves, skills): Enter or comma adds, Backspace on empty removes the last. */
export function ChipInput({
  value,
  onValueChange,
  placeholder,
  max,
  disabled,
  className,
}: ChipInputProps) {
  const field = useFieldControl();
  const [draft, setDraft] = useState("");
  const full = max !== undefined && value.length >= max;

  function add(raw: string) {
    const text = raw.trim().replace(/\s+/g, " ");
    if (!text || full) return;
    if (!value.some((chip) => chip.toLowerCase() === text.toLowerCase())) {
      onValueChange([...value, text]);
    }
    setDraft("");
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      add(draft);
    } else if (event.key === "Backspace" && draft === "" && value.length > 0) {
      onValueChange(value.slice(0, -1));
    }
  }

  return (
    <div
      className={cn(
        "flex min-h-12 w-full flex-wrap items-center gap-1.5 rounded-sm border border-line-strong bg-surface-raised px-2 py-1.5",
        "focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-focus",
        disabled && "opacity-60",
        className,
      )}
    >
      {value.map((chip) => (
        <span
          key={chip}
          className="inline-flex h-[30px] items-center gap-1 rounded-pill bg-evergreen-soft pr-1 pl-2.5 text-[13px] font-semibold text-evergreen"
        >
          {chip}
          <button
            type="button"
            disabled={disabled}
            aria-label={t("ui.remove", { label: chip })}
            onClick={() => onValueChange(value.filter((item) => item !== chip))}
            className="flex size-6 items-center justify-center rounded-pill hover:bg-surface-raised"
          >
            <XIcon aria-hidden="true" className="size-3.5" />
          </button>
        </span>
      ))}
      <input
        {...field}
        value={draft}
        disabled={disabled || full}
        placeholder={value.length === 0 ? placeholder : undefined}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={onKeyDown}
        onBlur={() => add(draft)}
        className="min-w-24 flex-1 bg-transparent px-1.5 py-1.5 text-base text-ink outline-none placeholder:text-ink-muted md:text-[15px]"
      />
    </div>
  );
}

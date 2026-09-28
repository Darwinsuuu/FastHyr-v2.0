"use client";

import * as RadixSwitch from "@radix-ui/react-switch";
import { type ReactNode, useId } from "react";

import { cn } from "@/lib/cn";

export interface ToggleProps {
  label: ReactNode;
  description?: ReactNode;
  checked?: boolean;
  defaultChecked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  name?: string;
  className?: string;
}

/** An on/off switch (44 × 26 track from the frames) with its label on the left. */
export function Toggle({ label, description, className, ...props }: ToggleProps) {
  const id = useId();
  return (
    <div className={cn("flex min-h-11 items-center justify-between gap-4 py-2", className)}>
      <div className="flex flex-col gap-0.5">
        <label htmlFor={id} className="cursor-pointer text-[15px] leading-5 font-semibold text-ink">
          {label}
        </label>
        {description && (
          <p id={`${id}-description`} className="text-[13px] leading-[18px] text-ink-muted">
            {description}
          </p>
        )}
      </div>
      <RadixSwitch.Root
        id={id}
        aria-describedby={description ? `${id}-description` : undefined}
        className={cn(
          "relative h-[26px] w-11 shrink-0 cursor-pointer rounded-pill bg-line-strong transition-colors duration-200 ease-out",
          "data-[state=checked]:bg-evergreen disabled:cursor-not-allowed disabled:opacity-50",
        )}
        {...props}
      >
        <RadixSwitch.Thumb
          className={cn(
            "block size-5 translate-x-[3px] rounded-pill bg-surface-raised shadow-[0_1px_2px_rgba(30,42,38,0.3)]",
            "transition-transform duration-200 ease-out data-[state=checked]:translate-x-[21px]",
          )}
        />
      </RadixSwitch.Root>
    </div>
  );
}

"use client";

import { CheckIcon, MinusIcon } from "@phosphor-icons/react";
import * as RadixCheckbox from "@radix-ui/react-checkbox";
import { type ReactNode, useId } from "react";

import { cn } from "@/lib/cn";

export interface CheckboxProps {
  label: ReactNode;
  /** Secondary line under the label. */
  description?: ReactNode;
  checked?: boolean | "indeterminate";
  defaultChecked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  name?: string;
  className?: string;
}

/** A checkbox with its label; the whole row is the touch target. */
export function Checkbox({
  label,
  description,
  onCheckedChange,
  className,
  ...props
}: CheckboxProps) {
  const id = useId();
  return (
    <div className={cn("flex min-h-11 items-start gap-3 py-2.5", className)}>
      <RadixCheckbox.Root
        id={id}
        aria-describedby={description ? `${id}-description` : undefined}
        onCheckedChange={(value) => onCheckedChange?.(value === true)}
        className={cn(
          "mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-[5px] border-[1.5px] border-line-strong bg-surface-raised",
          "data-[state=checked]:border-evergreen data-[state=checked]:bg-evergreen data-[state=checked]:text-on-evergreen",
          "data-[state=indeterminate]:border-evergreen data-[state=indeterminate]:bg-evergreen data-[state=indeterminate]:text-on-evergreen",
          "disabled:cursor-not-allowed disabled:opacity-50",
        )}
        {...props}
      >
        <RadixCheckbox.Indicator>
          {props.checked === "indeterminate" ? (
            <MinusIcon weight="bold" className="size-3.5" />
          ) : (
            <CheckIcon weight="bold" className="size-3.5" />
          )}
        </RadixCheckbox.Indicator>
      </RadixCheckbox.Root>
      <div className="flex flex-col gap-0.5">
        <label htmlFor={id} className="cursor-pointer text-[15px] leading-5 text-ink">
          {label}
        </label>
        {description && (
          <p id={`${id}-description`} className="text-[13px] leading-[18px] text-ink-muted">
            {description}
          </p>
        )}
      </div>
    </div>
  );
}

"use client";

import { CaretDownIcon, CheckIcon } from "@phosphor-icons/react";
import * as RadixSelect from "@radix-ui/react-select";

import { useFieldControl } from "@/components/ui/field";
import { controlClasses } from "@/components/ui/input";
import { cn } from "@/lib/cn";

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps {
  options: SelectOption[];
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  name?: string;
  size?: "md" | "sm";
  className?: string;
  "aria-label"?: string;
}

/** A single-choice dropdown (Radix Select: keyboard, typeahead, screen reader support). */
export function Select({ options, placeholder, size = "md", className, ...props }: SelectProps) {
  const field = useFieldControl();
  return (
    <RadixSelect.Root {...props} required={field.required}>
      <RadixSelect.Trigger
        id={field.id}
        aria-describedby={field["aria-describedby"]}
        aria-invalid={field["aria-invalid"]}
        aria-label={props["aria-label"]}
        className={cn(
          controlClasses,
          "flex items-center justify-between gap-2 text-left data-placeholder:text-ink-muted",
          size === "md" ? "h-12 px-3.5" : "h-10 px-3 md:text-[14px]",
          className,
        )}
      >
        <RadixSelect.Value placeholder={placeholder} />
        <RadixSelect.Icon>
          <CaretDownIcon aria-hidden="true" className="size-4 text-ink-muted" />
        </RadixSelect.Icon>
      </RadixSelect.Trigger>
      <RadixSelect.Portal>
        <RadixSelect.Content
          position="popper"
          sideOffset={6}
          collisionPadding={8}
          className={cn(
            "z-50 max-h-[min(var(--radix-select-content-available-height),320px)] min-w-[var(--radix-select-trigger-width)]",
            "overflow-hidden rounded-md border border-line bg-surface-raised p-1.5 shadow-raised",
          )}
        >
          <RadixSelect.Viewport>
            {options.map((option) => (
              <RadixSelect.Item
                key={option.value}
                value={option.value}
                disabled={option.disabled}
                className={cn(
                  "relative flex min-h-11 cursor-pointer items-center rounded-[8px] py-2 pr-3 pl-9 text-[15px] text-ink outline-none select-none",
                  "data-disabled:cursor-not-allowed data-disabled:opacity-50 data-highlighted:bg-surface-sunk",
                )}
              >
                <RadixSelect.ItemIndicator className="absolute left-3">
                  <CheckIcon aria-hidden="true" className="size-4 text-evergreen" />
                </RadixSelect.ItemIndicator>
                <RadixSelect.ItemText>{option.label}</RadixSelect.ItemText>
              </RadixSelect.Item>
            ))}
          </RadixSelect.Viewport>
        </RadixSelect.Content>
      </RadixSelect.Portal>
    </RadixSelect.Root>
  );
}

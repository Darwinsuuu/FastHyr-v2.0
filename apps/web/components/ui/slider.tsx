"use client";

import * as RadixSlider from "@radix-ui/react-slider";

import { useFieldControl } from "@/components/ui/field";
import { cn } from "@/lib/cn";

export interface SliderProps {
  value?: number;
  defaultValue?: number;
  onValueChange?: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  /** How the value is announced, e.g. (v) => `${v} out of 100`. */
  formatValue?: (value: number) => string;
  className?: string;
  "aria-label"?: string;
}

/** One-thumb slider for rubric weights and pass marks. Arrow keys move by `step`. */
export function Slider({
  value,
  defaultValue,
  onValueChange,
  formatValue,
  min = 0,
  max = 100,
  step = 1,
  className,
  ...props
}: SliderProps) {
  const field = useFieldControl();
  const current = value ?? defaultValue ?? min;
  return (
    <RadixSlider.Root
      value={value === undefined ? undefined : [value]}
      defaultValue={defaultValue === undefined ? undefined : [defaultValue]}
      onValueChange={(values) => onValueChange?.(values[0] ?? min)}
      min={min}
      max={max}
      step={step}
      disabled={props.disabled}
      className={cn("relative flex h-11 w-full touch-none items-center select-none", className)}
    >
      <RadixSlider.Track className="relative h-2 grow overflow-hidden rounded-pill bg-surface-sunk">
        <RadixSlider.Range className="absolute h-full rounded-pill bg-evergreen" />
      </RadixSlider.Track>
      <RadixSlider.Thumb
        id={field.id}
        aria-describedby={field["aria-describedby"]}
        aria-label={props["aria-label"]}
        aria-valuetext={formatValue?.(current)}
        className={cn(
          "block size-6 cursor-grab rounded-pill border-2 border-evergreen bg-surface-raised shadow-[0_1px_2px_rgba(30,42,38,0.3)]",
          "active:cursor-grabbing",
        )}
      />
    </RadixSlider.Root>
  );
}

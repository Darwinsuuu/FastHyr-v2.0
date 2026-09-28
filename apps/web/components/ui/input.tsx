"use client";

import { MagnifyingGlassIcon } from "@phosphor-icons/react";
import { forwardRef, type InputHTMLAttributes, type TextareaHTMLAttributes } from "react";

import { useFieldControl } from "@/components/ui/field";
import { cn } from "@/lib/cn";

/** Shared look for text controls: 48 px, radius-sm, line-strong border, 16 px text on phones. */
export const controlClasses = cn(
  "w-full rounded-sm border border-line-strong bg-surface-raised text-ink",
  "text-base md:text-[15px] placeholder:text-ink-muted",
  "transition-colors duration-200 ease-out hover:border-ink",
  "aria-invalid:border-signal-gap disabled:cursor-not-allowed disabled:opacity-60",
);

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return (
      <input
        ref={ref}
        className={cn(controlClasses, "h-12 px-3.5", className)}
        {...useFieldControl()}
        {...props}
      />
    );
  },
);

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, rows = 4, ...props }, ref) {
  return (
    <textarea
      ref={ref}
      rows={rows}
      className={cn(controlClasses, "min-h-24 px-3.5 py-3 leading-6", className)}
      {...useFieldControl()}
      {...props}
    />
  );
});

/** Search box with a leading icon; type="search" gives phones the right keyboard. */
export const SearchInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function SearchInput({ className, ...props }, ref) {
    return (
      <div className={cn("relative", className)}>
        <MagnifyingGlassIcon
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 left-3 size-5 -translate-y-1/2 text-ink-muted"
        />
        <input
          ref={ref}
          type="search"
          className={cn(controlClasses, "h-11 pr-3 pl-10")}
          {...useFieldControl()}
          {...props}
        />
      </div>
    );
  },
);

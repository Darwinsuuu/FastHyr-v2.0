"use client";

import * as RadixTabs from "@radix-ui/react-tabs";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export interface TabItem {
  value: string;
  label: string;
  /** Optional count after the label, e.g. candidates in a stage. */
  count?: number;
  content: ReactNode;
}

export interface TabsProps {
  items: TabItem[];
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  /** Names the tab list for screen readers. */
  label: string;
  className?: string;
}

/** Underline tabs (pipeline, profile). The list scrolls sideways on phones instead of wrapping. */
export function Tabs({ items, value, defaultValue, onValueChange, label, className }: TabsProps) {
  return (
    <RadixTabs.Root
      value={value}
      defaultValue={defaultValue ?? items[0]?.value}
      onValueChange={onValueChange}
      className={className}
    >
      <RadixTabs.List
        aria-label={label}
        className="-mx-4 flex gap-5 overflow-x-auto border-b border-line px-4 [scrollbar-width:none] md:mx-0 md:gap-6 md:px-0"
      >
        {items.map((item) => (
          <RadixTabs.Trigger
            key={item.value}
            value={item.value}
            className={cn(
              "-mb-px flex min-h-11 shrink-0 items-center gap-1.5 border-b-2 border-transparent text-[14px] font-semibold whitespace-nowrap text-ink-muted",
              "transition-colors duration-200 ease-out hover:text-ink",
              "data-[state=active]:border-evergreen data-[state=active]:text-ink",
            )}
          >
            {item.label}
            {item.count !== undefined && (
              <span className="rounded-pill bg-surface-sunk px-1.5 text-[12px] leading-5 text-ink-muted tabular-nums">
                {item.count}
              </span>
            )}
          </RadixTabs.Trigger>
        ))}
      </RadixTabs.List>
      {items.map((item) => (
        <RadixTabs.Content key={item.value} value={item.value} className="pt-5">
          {item.content}
        </RadixTabs.Content>
      ))}
    </RadixTabs.Root>
  );
}

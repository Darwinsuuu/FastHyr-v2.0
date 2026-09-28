import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export type BadgeTone =
  "neutral" | "evergreen" | "persimmon" | "strong" | "watch" | "gap" | "outline";

const TONES: Record<BadgeTone, string> = {
  neutral: "bg-surface-sunk text-ink",
  evergreen: "bg-evergreen-soft text-evergreen",
  persimmon: "bg-persimmon-soft text-persimmon-ink",
  strong: "border border-signal-strong text-signal-strong",
  watch: "border border-signal-watch text-signal-watch",
  gap: "border border-signal-gap text-signal-gap",
  outline: "border border-line-strong text-ink-muted",
};

/** A small label (role, plan, "New"). 22 px high, 12 px / 650. */
export function Badge({
  tone = "neutral",
  icon,
  children,
  className,
}: {
  tone?: BadgeTone;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex h-[22px] shrink-0 items-center gap-1 rounded-pill px-2 text-[12px] leading-4 font-[650] whitespace-nowrap",
        "[&>svg]:size-3.5",
        TONES[tone],
        className,
      )}
    >
      {icon}
      {children}
    </span>
  );
}

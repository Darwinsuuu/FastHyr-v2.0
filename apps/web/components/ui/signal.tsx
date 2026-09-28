import type { ReactNode } from "react";

import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";

export type SignalLevel = "strong" | "watch" | "gap";

const LEVEL_CLASSES: Record<SignalLevel, { text: string; glyph: string }> = {
  strong: { text: "text-signal-strong", glyph: "bg-current" },
  watch: {
    text: "text-signal-watch",
    glyph: "bg-[linear-gradient(90deg,currentColor_50%,transparent_50%)]",
  },
  gap: { text: "text-signal-gap", glyph: "" },
};

/**
 * An evidence signal: glyph + word, never colour alone (filled disc, half disc, ring).
 * Hiring side only. `gap` means "not shown on the résumé yet", never "reject".
 */
export function Signal({
  level,
  children,
  className,
}: {
  level: SignalLevel;
  children?: ReactNode;
  className?: string;
}) {
  const classes = LEVEL_CLASSES[level];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-pill border border-line bg-surface-raised py-[3px] pr-2.5 pl-2 text-[13px] leading-[18px] font-semibold whitespace-nowrap",
        classes.text,
        className,
      )}
    >
      <span
        aria-hidden="true"
        className={cn("size-2.5 shrink-0 rounded-pill border-2 border-current", classes.glyph)}
      />
      {children ?? t(`signal.${level}`)}
    </span>
  );
}

/** "4 strong · 2 worth probing · 1 not evidenced yet": a candidate summarised by counts, never a percentage. */
export function SignalCounts({
  counts,
  className,
}: {
  counts: Partial<Record<SignalLevel, number>>;
  className?: string;
}) {
  const levels = (["strong", "watch", "gap"] as const).filter((level) => (counts[level] ?? 0) > 0);
  return (
    <span
      className={cn(
        "inline-flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-ink",
        className,
      )}
    >
      {levels.map((level, index) => (
        <span key={level} className="inline-flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className={cn(
              "size-2.5 rounded-pill border-2 border-current",
              LEVEL_CLASSES[level].text,
              LEVEL_CLASSES[level].glyph,
            )}
          />
          {counts[level]} {t(`signal.${level}`).toLowerCase()}
          {index < levels.length - 1 && (
            <span aria-hidden="true" className="text-ink-muted">
              ·
            </span>
          )}
        </span>
      ))}
    </span>
  );
}

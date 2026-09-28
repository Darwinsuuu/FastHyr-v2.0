import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";

export interface ScoreBarProps {
  value: number;
  max?: number;
  /** Draws a persimmon-ink tick at the pass mark. */
  passMark?: number;
  /** Bar thickness from the frames: 6 (lists), 8 (breakdowns), 10 (funnels). */
  size?: 6 | 8 | 10;
  /** Fill colour class; evergreen by default. */
  fillClassName?: string;
  /** Accessible name, e.g. "Technical fit". */
  label: string;
  className?: string;
}

/** A score as a bar. Hiring side only: candidates never see scores. */
export function ScoreBar({
  value,
  max = 100,
  passMark,
  size = 8,
  fillClassName,
  label,
  className,
}: ScoreBarProps) {
  const percent = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
      aria-valuetext={t("score.outOf", { value, max })}
      className={cn("relative w-full", className)}
    >
      <div className="overflow-hidden rounded-pill bg-surface-sunk" style={{ height: size }}>
        <div
          className={cn("h-full rounded-pill bg-evergreen", fillClassName)}
          style={{ width: `${percent}%` }}
        />
      </div>
      {passMark !== undefined && (
        <span
          aria-hidden="true"
          className="absolute w-0.5 rounded-pill bg-persimmon-ink"
          style={{ left: `${(passMark / max) * 100}%`, top: -3, height: size + 6 }}
        />
      )}
    </div>
  );
}

import { Fragment } from "react";

import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";
import { t } from "@/lib/i18n";

export interface WeightedItem {
  label: string;
  /** 0–100. */
  score: number;
  /** Percent of the total, e.g. 50. Weights add up to 100. */
  weight: number;
}

// Series order from the frames: evergreen, then the lighter chart greens.
const SERIES = [
  { fill: "bg-evergreen", border: "border-t-evergreen" },
  { fill: "bg-chart-2", border: "border-t-chart-2" },
  { fill: "bg-chart-3", border: "border-t-chart-3" },
  { fill: "bg-chart-muted", border: "border-t-chart-muted" },
];

/** Points per criterion (score × weight) and the total, exact and rounded to a whole score. */
export function weightedTotal(items: WeightedItem[]): {
  points: number[];
  exact: number;
  rounded: number;
} {
  const points = items.map((item) => (item.score * item.weight) / 100);
  const exact = Math.round(points.reduce((sum, value) => sum + value, 0) * 10) / 10;
  return { points, exact, rounded: Math.round(exact) };
}

const one = (value: number) => formatNumber(Math.round(value * 10) / 10, undefined);
const oneDecimal = (value: number) =>
  new Intl.NumberFormat(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(
    value,
  );

export interface WeightedCalcProps {
  items: WeightedItem[];
  passMark?: number;
  /** Line under the calculation, e.g. when the rubric was locked. */
  note?: string;
  className?: string;
}

/**
 * "How we got to 91": each criterion score times its weight, added up, with the points bar against
 * the pass mark. Every score shows its calculation (hard rule 5). Hiring side only.
 */
export function WeightedCalc({ items, passMark, note, className }: WeightedCalcProps) {
  const { points, exact, rounded } = weightedTotal(items);
  return (
    <div className={cn("flex flex-col gap-4", className)}>
      <div className="flex flex-col gap-2.5 md:flex-row md:items-stretch">
        {items.map((item, index) => {
          const series = SERIES[index % SERIES.length] ?? SERIES[0];
          return (
            <Fragment key={item.label}>
              {index > 0 && (
                <span
                  aria-hidden="true"
                  className="hidden self-center text-[20px] text-line-strong md:block"
                >
                  +
                </span>
              )}
              <div
                className={cn("flex-1 rounded-[12px] border-t-4 bg-surface p-3.5", series?.border)}
              >
                <p className="text-[13px] font-[650] text-ink">{item.label}</p>
                <p className="mt-1 text-[14px] text-ink-muted">
                  <span className="text-[20px] font-semibold text-ink tabular-nums">
                    {item.score}
                  </span>{" "}
                  × {item.weight}%
                </p>
                <p className="text-[14px] text-ink-muted">
                  {t("score.points", { points: oneDecimal(points[index] ?? 0) })}
                </p>
              </div>
            </Fragment>
          );
        })}
        <span
          aria-hidden="true"
          className="hidden self-center text-[20px] text-line-strong md:block"
        >
          =
        </span>
        <div className="flex items-center justify-between gap-3 rounded-[12px] bg-evergreen p-3.5 text-on-evergreen md:w-[120px] md:flex-col md:items-start md:justify-center">
          <p className="text-[13px] opacity-85">{t("score.rounded", { value: one(exact) })}</p>
          <p className="font-display text-[32px] leading-9 font-[560] tabular-nums">{rounded}</p>
        </div>
      </div>

      <div aria-hidden="true" className="pt-2">
        <div className="relative">
          <div className="flex h-4 overflow-hidden rounded-pill bg-surface-sunk">
            {points.map((value, index) => (
              <span
                key={items[index]?.label}
                className={cn("h-full", SERIES[index % SERIES.length]?.fill)}
                style={{ width: `${value}%` }}
              />
            ))}
          </div>
          {passMark !== undefined && (
            <span
              className="absolute -top-[5px] h-[26px] w-0.5 bg-persimmon-ink"
              style={{ left: `${passMark}%` }}
            />
          )}
        </div>
        <div className="relative mt-2 flex justify-between text-[12px] text-ink-muted">
          <span>0</span>
          {passMark !== undefined && (
            <span
              className="absolute -translate-x-1/2 font-[650] whitespace-nowrap text-persimmon-ink"
              style={{ left: `${passMark}%` }}
            >
              {t("score.passMark", { value: passMark })}
            </span>
          )}
          <span>100</span>
        </div>
      </div>
      {note && <p className="text-[12px] leading-[18px] text-ink-muted">{note}</p>}
    </div>
  );
}

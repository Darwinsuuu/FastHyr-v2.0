"use client";

import { useState } from "react";

import { ChartFrame, Legend } from "@/components/charts/chart-frame";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";

export interface BarSeries {
  name: string;
  /** Fill class, e.g. "bg-chart-3". */
  fill: string;
}

export interface BarDatum {
  label: string;
  /** One value per series. */
  values: number[];
}

export interface BarChartProps {
  title: string;
  series: BarSeries[];
  data: BarDatum[];
  /**
   * overlay: later series drawn inside the first from the bottom (applied vs passed).
   * stacked: series stacked on top of each other (plan + extra credits).
   */
  mode?: "overlay" | "stacked";
  /** Scale top; defaults to the largest bar. */
  max?: number;
  /** Plot height in px (the frames use 140–220). */
  height?: number;
  /** Always print the total above each bar; otherwise it shows on hover, focus or tap. */
  showValues?: boolean;
  /** A horizontal dashed line (e.g. plan allowance). */
  referenceLine?: { value: number; label: string };
  /** A vertical dashed line before bar index `beforeIndex` (e.g. the pass mark in a histogram). */
  marker?: { beforeIndex: number; label: string };
  /** Per-bar fill override for the first series, e.g. bins below the pass mark. */
  fillFor?: (datum: BarDatum, index: number) => string | undefined;
  /** Show every nth x label so labels don't collide. */
  labelEvery?: number;
  /** Same, below md (defaults to `labelEvery`). */
  phoneLabelEvery?: number;
  /** Show the legend (below the chart). */
  legend?: boolean;
  className?: string;
}

/** Vertical bars: weekly applicants, per-day applicants, histograms and monthly credits. */
export function BarChart({
  title,
  series,
  data,
  mode = "overlay",
  max,
  height = 170,
  showValues = true,
  referenceLine,
  marker,
  fillFor,
  labelEvery = 1,
  phoneLabelEvery = labelEvery,
  legend = series.length > 1,
  className,
}: BarChartProps) {
  const [active, setActive] = useState<number | null>(null);
  const totals = data.map((datum) =>
    mode === "stacked"
      ? datum.values.reduce((sum, value) => sum + value, 0)
      : (datum.values[0] ?? 0),
  );
  const top = max ?? Math.max(1, ...totals, referenceLine?.value ?? 0);
  const pct = (value: number) => `${(value / top) * 100}%`;

  return (
    <ChartFrame
      title={title}
      columns={series.map((item) => item.name)}
      data={data.map((datum) => ({
        label: datum.label,
        values: datum.values.map((value) => formatNumber(value)),
      }))}
      className={className}
    >
      <div className="relative pt-6" style={{ height: height + 24 }}>
        {referenceLine && (
          <div
            className="pointer-events-none absolute inset-x-0 z-10 border-t-2 border-dashed border-persimmon-ink"
            style={{ bottom: pct(referenceLine.value) }}
          >
            <span className="absolute -top-5 right-0 bg-surface-raised px-1 text-[11px] font-semibold text-persimmon-ink">
              {referenceLine.label}
            </span>
          </div>
        )}
        <div className="flex h-full items-end gap-1 border-b border-line sm:gap-2.5 md:gap-4">
          {data.map((datum, index) => {
            const total = totals[index] ?? 0;
            const showValue = showValues || active === index;
            return (
              <div key={datum.label} className="relative flex h-full min-w-0 flex-1 items-end">
                {marker && marker.beforeIndex === index && (
                  <div className="pointer-events-none absolute top-0 bottom-0 -left-[3px] z-10 border-l-2 border-dashed border-persimmon-ink sm:-left-2 md:-left-3">
                    <span className="absolute -top-5 left-1 text-[11px] font-semibold whitespace-nowrap text-persimmon-ink">
                      {marker.label}
                    </span>
                  </div>
                )}
                <button
                  type="button"
                  tabIndex={-1}
                  onPointerEnter={() => setActive(index)}
                  onPointerLeave={() => setActive(null)}
                  onClick={() => setActive(active === index ? null : index)}
                  className="relative flex h-full w-full cursor-default flex-col justify-end"
                >
                  {showValue && (
                    <span
                      className="absolute left-1/2 -translate-x-1/2 text-[12px] font-[650] text-ink tabular-nums"
                      style={{ bottom: `calc(${pct(total)} + 4px)` }}
                    >
                      {formatNumber(total)}
                    </span>
                  )}
                  {mode === "stacked" ? (
                    <span
                      className="flex w-full flex-col-reverse overflow-hidden rounded-t-[6px]"
                      style={{ height: pct(total) }}
                    >
                      {datum.values.map((value, seriesIndex) => (
                        <span
                          key={series[seriesIndex]?.name ?? seriesIndex}
                          className={cn(
                            "w-full",
                            (seriesIndex === 0 && fillFor?.(datum, index)) ||
                              series[seriesIndex]?.fill,
                          )}
                          style={{ height: `${total > 0 ? (value / total) * 100 : 0}%` }}
                        />
                      ))}
                    </span>
                  ) : (
                    <span
                      className={cn(
                        "relative w-full overflow-hidden rounded-t-[6px] transition-colors",
                        fillFor?.(datum, index) ?? series[0]?.fill,
                        active !== null && active !== index && "opacity-60",
                      )}
                      style={{ height: pct(total) }}
                    >
                      {datum.values.slice(1).map((value, seriesIndex) => (
                        <span
                          key={series[seriesIndex + 1]?.name ?? seriesIndex}
                          className={cn(
                            "absolute inset-x-0 bottom-0",
                            series[seriesIndex + 1]?.fill,
                          )}
                          style={{ height: `${total > 0 ? (value / total) * 100 : 0}%` }}
                        />
                      ))}
                    </span>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </div>
      <div className="mt-2 flex gap-1 sm:gap-2.5 md:gap-4">
        {data.map((datum, index) => (
          <span
            key={datum.label}
            className={cn(
              "min-w-0 flex-1 text-center text-[11px] whitespace-nowrap text-ink-muted md:text-[12px]",
              index % phoneLabelEvery !== 0 && "invisible md:visible",
              index % labelEvery !== 0 && "md:invisible",
            )}
          >
            {datum.label}
          </span>
        ))}
      </div>
      {legend && (
        <Legend
          className="mt-3"
          items={series.map((item) => ({ label: item.name, swatch: item.fill }))}
        />
      )}
    </ChartFrame>
  );
}

import { ChartFrame } from "@/components/charts/chart-frame";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";
import { t } from "@/lib/i18n";

export interface HorizontalBar {
  label: string;
  value: number;
  /** Secondary text after the value, e.g. "60% of applicants". */
  note?: string;
  /** Fill class; evergreen by default. */
  fill?: string;
}

export interface HorizontalBarsProps {
  title: string;
  rows: HorizontalBar[];
  /** Scale end; defaults to the largest value. */
  max?: number;
  /** Bar thickness from the frames: 8, 10 or 22. */
  size?: 8 | 10 | 22;
  /** Column header for the screen-reader table. */
  valueLabel?: string;
  className?: string;
}

/**
 * Labelled horizontal bars: the candidate funnel, sources, departments, and comparisons.
 * On phones the label sits above its bar; from md label, bar and value share a row.
 */
export function HorizontalBars({
  title,
  rows,
  max,
  size = 10,
  valueLabel = t("charts.value"),
  className,
}: HorizontalBarsProps) {
  const top = max ?? Math.max(1, ...rows.map((row) => row.value));
  return (
    <ChartFrame
      title={title}
      columns={rows.some((row) => row.note) ? [valueLabel, ""] : [valueLabel]}
      data={rows.map((row) => ({
        label: row.label,
        values: row.note ? [formatNumber(row.value), row.note] : [formatNumber(row.value)],
      }))}
      className={className}
    >
      <ul className="flex flex-col gap-3.5">
        {rows.map((row) => (
          <li
            key={row.label}
            className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1.5 md:grid-cols-[130px_1fr_auto]"
          >
            <span className="truncate text-[14px] text-ink">{row.label}</span>
            <span className="col-span-2 row-start-2 overflow-hidden rounded-pill bg-surface md:col-span-1 md:row-start-auto">
              <span
                className={cn("block rounded-pill", row.fill ?? "bg-evergreen")}
                style={{
                  height: size,
                  width: `${Math.max(0, Math.min(100, (row.value / top) * 100))}%`,
                }}
              />
            </span>
            <span className="text-right whitespace-nowrap">
              <span className="text-[15px] font-bold text-ink tabular-nums">
                {formatNumber(row.value)}
              </span>
              {row.note && <span className="ml-1.5 text-[13px] text-ink-muted">{row.note}</span>}
            </span>
          </li>
        ))}
      </ul>
    </ChartFrame>
  );
}

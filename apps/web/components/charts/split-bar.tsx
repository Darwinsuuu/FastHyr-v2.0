import { ChartFrame } from "@/components/charts/chart-frame";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";
import { t } from "@/lib/i18n";

export interface SplitSegment {
  label: string;
  value: number;
  /** Fill class, e.g. "bg-chart-amber". */
  fill: string;
}

/** One bar split into parts (credits reserved vs free, unfinished interview reasons) with a value legend. */
export function SplitBar({
  title,
  segments,
  size = 14,
  className,
}: {
  title: string;
  segments: SplitSegment[];
  size?: 12 | 14 | 18;
  className?: string;
}) {
  const total = segments.reduce((sum, segment) => sum + segment.value, 0);
  return (
    <ChartFrame
      title={title}
      columns={[t("charts.value")]}
      data={segments.map((segment) => ({
        label: segment.label,
        values: [formatNumber(segment.value)],
      }))}
      className={className}
    >
      <div className="flex gap-[3px]" style={{ height: size }}>
        {segments.map((segment) => (
          <span
            key={segment.label}
            className={cn("h-full first:rounded-l-[6px] last:rounded-r-[6px]", segment.fill)}
            style={{ width: `${total > 0 ? (segment.value / total) * 100 : 0}%` }}
          />
        ))}
      </div>
      <ul className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
        {segments.map((segment) => (
          <li
            key={segment.label}
            className="flex items-center gap-2 sm:flex-col sm:items-start sm:gap-0.5"
          >
            <span className="inline-flex items-center gap-1.5 text-[12px] text-ink-muted">
              <span className={cn("size-2.5 rounded-[3px]", segment.fill)} />
              {segment.label}
            </span>
            <span className="ml-auto text-[15px] font-bold text-ink tabular-nums sm:ml-0 sm:text-[20px]">
              {formatNumber(segment.value)}
            </span>
          </li>
        ))}
      </ul>
    </ChartFrame>
  );
}

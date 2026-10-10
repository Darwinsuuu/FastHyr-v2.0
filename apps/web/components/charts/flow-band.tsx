import { ChartFrame } from "@/components/charts/chart-frame";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";
import { t } from "@/lib/i18n";

export interface FlowStage {
  label: string;
  value: number;
  /** e.g. "60% of applicants". */
  note?: string;
  /** A muted line under the number, e.g. "35 résumés not a match". */
  detail?: string;
  /** Draws the label and number in persimmon, for the stage that waits on the reader. */
  attention?: boolean;
}

// Stage colours from the frames: evergreen → lighter greens → persimmon for "Ready".
const FILLS = ["fill-evergreen", "fill-chart-2", "fill-chart-3", "fill-persimmon"];
const RULES = ["border-evergreen", "border-chart-2", "border-chart-3", "border-persimmon"];

/**
 * How candidates flow through a pipeline: stage numbers above a band whose height follows the count.
 * Stats wrap to two columns on phones.
 */
export function FlowBand({
  title,
  stages,
  className,
}: {
  title: string;
  stages: FlowStage[];
  className?: string;
}) {
  const top = Math.max(1, ...stages.map((stage) => stage.value));
  const width = 1000;
  const gap = 3;
  const step = width / stages.length;
  const half = (value: number) => Math.max(4, (value / top) * 40);
  const next = (index: number) => stages[index + 1]?.value ?? stages[index]?.value ?? 0;

  return (
    <ChartFrame
      title={title}
      columns={[t("charts.candidates"), ""]}
      data={stages.map((stage) => ({
        label: stage.label,
        values: [formatNumber(stage.value), stage.note ?? ""],
      }))}
      className={className}
    >
      <ul className="grid grid-cols-2 gap-x-4 gap-y-5 md:grid-cols-4">
        {stages.map((stage, index) => (
          <li key={stage.label} className={cn("border-l-2 pl-3", RULES[index % RULES.length])}>
            <p
              className={cn(
                "type-label",
                stage.attention ? "text-persimmon-ink" : "text-ink-muted",
              )}
            >
              {stage.label}
            </p>
            <p
              className={cn(
                "font-display text-[36px] leading-[42px] font-[560] tabular-nums md:text-[44px] md:leading-[50px]",
                stage.attention ? "text-persimmon-ink" : "text-ink",
              )}
            >
              {formatNumber(stage.value)}
            </p>
            {stage.note && <p className="text-[13px] font-semibold text-ink-muted">{stage.note}</p>}
            {stage.detail && (
              <p className="mt-0.5 text-[13px] leading-[18px] text-ink-muted">{stage.detail}</p>
            )}
          </li>
        ))}
      </ul>
      <svg
        viewBox={`0 0 ${width} 88`}
        preserveAspectRatio="none"
        className="mt-4 h-16 w-full md:h-[88px]"
      >
        {stages.map((stage, index) => {
          const x0 = index * step + (index > 0 ? gap / 2 : 0);
          const x1 = (index + 1) * step - (index < stages.length - 1 ? gap / 2 : 0);
          const a = half(stage.value);
          const b = half(next(index));
          return (
            <polygon
              key={stage.label}
              points={`${x0},${44 - a} ${x1},${44 - b} ${x1},${44 + b} ${x0},${44 + a}`}
              className={FILLS[index % FILLS.length]}
            />
          );
        })}
      </svg>
    </ChartFrame>
  );
}

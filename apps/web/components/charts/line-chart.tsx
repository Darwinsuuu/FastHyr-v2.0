import { ChartFrame } from "@/components/charts/chart-frame";
import { formatNumber } from "@/lib/format";
import { t } from "@/lib/i18n";

export interface LinePoint {
  label: string;
  value: number;
}

const WIDTH = 520;
const HEIGHT = 190;
const PAD = { top: 28, right: 24, bottom: 28, left: 24 };

// SVG text scales with the chart, so labels are larger below md, where the chart is drawn smaller.

/** A score over time (a candidate's history) with a dashed pass-mark line; the latest point is persimmon. */
export function LineChart({
  title,
  points,
  passMark,
  passMarkLabel,
  min,
  max = 100,
  className,
}: {
  title: string;
  points: LinePoint[];
  passMark?: number;
  passMarkLabel?: string;
  /** Scale bottom; defaults to 10 below the lowest point or pass mark. */
  min?: number;
  max?: number;
  className?: string;
}) {
  const lowest = Math.min(...points.map((point) => point.value), passMark ?? max);
  const bottom = min ?? Math.max(0, Math.floor((lowest - 10) / 10) * 10);
  const plotW = WIDTH - PAD.left - PAD.right;
  const plotH = HEIGHT - PAD.top - PAD.bottom;
  const x = (index: number) =>
    PAD.left + (points.length > 1 ? (index / (points.length - 1)) * plotW : plotW / 2);
  const y = (value: number) => PAD.top + (1 - (value - bottom) / (max - bottom)) * plotH;
  const path = points.map((point, index) => `${x(index)},${y(point.value)}`).join(" ");

  return (
    <ChartFrame
      title={title}
      columns={[t("charts.score")]}
      data={points.map((point) => ({ label: point.label, values: [formatNumber(point.value)] }))}
      className={className}
    >
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full overflow-visible">
        <line
          x1={PAD.left}
          x2={WIDTH - PAD.right}
          y1={HEIGHT - PAD.bottom}
          y2={HEIGHT - PAD.bottom}
          className="stroke-line"
        />
        {passMark !== undefined && (
          <g>
            <line
              x1={PAD.left}
              x2={WIDTH - PAD.right}
              y1={y(passMark)}
              y2={y(passMark)}
              className="stroke-persimmon-ink"
              strokeWidth={1.5}
              strokeDasharray="5 4"
            />
            <text
              x={WIDTH - PAD.right}
              y={y(passMark) + 16}
              textAnchor="end"
              className="fill-persimmon-ink text-[19px] font-semibold md:text-[11px]"
            >
              {passMarkLabel}
            </text>
          </g>
        )}
        <polyline
          points={path}
          className="fill-none stroke-evergreen"
          strokeWidth={2.5}
          strokeLinejoin="round"
        />
        {points.map((point, index) => {
          const last = index === points.length - 1;
          return (
            <g key={point.label}>
              <circle
                cx={x(index)}
                cy={y(point.value)}
                r={6}
                strokeWidth={2}
                className={
                  last
                    ? "fill-persimmon stroke-surface-raised"
                    : "fill-evergreen stroke-surface-raised"
                }
              />
              <text
                x={x(index)}
                y={y(point.value) - 12}
                textAnchor="middle"
                className="fill-ink text-[22px] font-bold md:text-[14px]"
              >
                {formatNumber(point.value)}
              </text>
              <text
                x={x(index)}
                y={HEIGHT - 8}
                textAnchor="middle"
                className="fill-ink-muted text-[20px] md:text-[12px]"
              >
                {point.label}
              </text>
            </g>
          );
        })}
      </svg>
    </ChartFrame>
  );
}

import { ChartFrame, Legend } from "@/components/charts/chart-frame";

export interface RadarSeries {
  name: string;
  /** 0–100, one per axis. */
  values: number[];
  /** primary: evergreen filled; comparison: muted and dashed (the pipeline average). */
  variant: "primary" | "comparison";
}

const SIZE = 300;
const CENTER = { x: 150, y: 130 };
const RADIUS = 95;

function point(axis: number, count: number, value: number) {
  const angle = (Math.PI * 2 * axis) / count - Math.PI / 2;
  const r = (Math.max(0, Math.min(100, value)) / 100) * RADIUS;
  return { x: CENTER.x + r * Math.cos(angle), y: CENTER.y + r * Math.sin(angle) };
}

const polygon = (values: number[]) =>
  values
    .map((value, index) => point(index, values.length, value))
    .map(({ x, y }) => `${x.toFixed(1)},${y.toFixed(1)}`)
    .join(" ");

/** Interview topic scores against the pipeline average, on rings at 25/50/75/100. */
export function RadarChart({
  title,
  axes,
  series,
  className,
}: {
  title: string;
  axes: string[];
  series: RadarSeries[];
  className?: string;
}) {
  return (
    <ChartFrame
      title={title}
      columns={series.map((item) => item.name)}
      data={axes.map((axis, index) => ({
        label: axis,
        values: series.map((item) => item.values[index] ?? 0),
      }))}
      className={className}
    >
      <svg viewBox={`-70 0 ${SIZE + 140} 260`} className="mx-auto w-full max-w-[440px]">
        {[25, 50, 75, 100].map((ring) => (
          <polygon
            key={ring}
            points={polygon(axes.map(() => ring))}
            className="fill-none stroke-line"
          />
        ))}
        {axes.map((axis, index) => {
          const end = point(index, axes.length, 100);
          const label = point(index, axes.length, 122);
          const anchor =
            Math.abs(label.x - CENTER.x) < 4 ? "middle" : label.x > CENTER.x ? "start" : "end";
          return (
            <g key={axis}>
              <line x1={CENTER.x} y1={CENTER.y} x2={end.x} y2={end.y} className="stroke-line" />
              <text
                x={label.x}
                y={label.y + 4}
                textAnchor={anchor}
                className="fill-ink-muted text-[16px] md:text-[11px]"
              >
                {axis}
              </text>
            </g>
          );
        })}
        {series.map((item) =>
          item.variant === "primary" ? (
            <polygon
              key={item.name}
              points={polygon(item.values)}
              className="fill-evergreen/20 stroke-evergreen"
              strokeWidth={2}
            />
          ) : (
            <polygon
              key={item.name}
              points={polygon(item.values)}
              className="fill-chart-muted/25 stroke-line-strong"
              strokeWidth={1.5}
              strokeDasharray="4 3"
            />
          ),
        )}
      </svg>
      <Legend
        className="mt-2 justify-center"
        items={series.map((item) => ({
          label: item.name,
          swatch: item.variant === "primary" ? "bg-evergreen" : "border-line-strong",
          kind: item.variant === "primary" ? "box" : "line",
        }))}
      />
    </ChartFrame>
  );
}

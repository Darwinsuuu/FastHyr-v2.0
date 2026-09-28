import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export interface ChartDatum {
  label: string;
  /** Formatted values in column order. */
  values: (string | number)[];
}

/**
 * Wraps a chart: the visual is hidden from screen readers and a plain table carries the same data
 * (every chart has a text equivalent).
 */
export function ChartFrame({
  title,
  columns,
  data,
  children,
  className,
}: {
  /** Names the figure, e.g. "Applicants per week". */
  title: string;
  /** Header for each value column, e.g. ["Applied", "Passed the interview"]. */
  columns: string[];
  data: ChartDatum[];
  children: ReactNode;
  className?: string;
}) {
  return (
    <figure className={cn("m-0 w-full min-w-0", className)}>
      <div aria-hidden="true">{children}</div>
      {/* A table ignores width and overflow, so the sr-only box wraps it. */}
      <div className="sr-only">
        <table>
          <caption>{title}</caption>
          <thead>
            <tr>
              <th scope="col" />
              {columns.map((column) => (
                <th key={column} scope="col">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((datum) => (
              <tr key={datum.label}>
                <th scope="row">{datum.label}</th>
                {datum.values.map((value, index) => (
                  <td key={columns[index] ?? index}>{value}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}

export interface LegendItem {
  label: string;
  /** Swatch colour class, e.g. "bg-evergreen". */
  swatch: string;
  /** "line" draws a dashed pass-mark style swatch. */
  kind?: "box" | "line";
}

/** 10 px swatches, 12 px muted labels; placed below the chart on phones. */
export function Legend({ items, className }: { items: LegendItem[]; className?: string }) {
  return (
    <ul
      aria-hidden="true"
      className={cn("flex flex-wrap gap-x-3.5 gap-y-1.5 text-[12px] text-ink-muted", className)}
    >
      {items.map((item) => (
        <li key={item.label} className="inline-flex items-center gap-1.5">
          {item.kind === "line" ? (
            <span className={cn("h-0 w-3.5 border-t-2 border-dashed", item.swatch)} />
          ) : (
            <span className={cn("size-2.5 rounded-[3px]", item.swatch)} />
          )}
          {item.label}
        </li>
      ))}
    </ul>
  );
}

import type { ReactNode } from "react";

import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";

export interface Column<T> {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  /** Hide lower-priority columns until this breakpoint (the card list covers phones). */
  showFrom?: "lg" | "xl";
  align?: "start" | "end";
  /** e.g. "w-[210px]". */
  className?: string;
}

export interface TableProps<T> {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string;
  /** Names the table for screen readers, e.g. "Pipelines". */
  caption: string;
  /** Phone layout (below md): one card per row with the primary field, a status pill and one or two numbers. */
  card: (row: T) => ReactNode;
  /** Row actions, usually a Menu; shown in the last column and in the card's corner. */
  rowMenu?: (row: T) => ReactNode;
  /** Shown instead of the rows when there are none (an EmptyState). */
  empty?: ReactNode;
  /** Pagination sits under the rows, inside the frame. */
  footer?: ReactNode;
  className?: string;
}

const SHOW_FROM = { lg: "hidden lg:table-cell", xl: "hidden xl:table-cell" };

/**
 * TA-density table inside a bordered card. From md it is a real <table>; below md each row is a card.
 * No stripes; rows highlight on hover.
 */
export function Table<T>({
  rows,
  columns,
  rowKey,
  caption,
  card,
  rowMenu,
  empty,
  footer,
  className,
}: TableProps<T>) {
  return (
    <div
      className={cn("overflow-hidden rounded-md border border-line bg-surface-raised", className)}
    >
      {rows.length === 0 && empty ? (
        empty
      ) : (
        <>
          <ul aria-label={caption} className="divide-y divide-line md:hidden">
            {rows.map((row) => (
              <li key={rowKey(row)} className="relative flex items-start gap-3 p-4">
                <div className="min-w-0 flex-1">{card(row)}</div>
                {rowMenu && <div className="-my-1 -mr-2 shrink-0">{rowMenu(row)}</div>}
              </li>
            ))}
          </ul>
          <table className="hidden w-full border-collapse text-left text-[14px] text-ink md:table">
            <caption className="sr-only">{caption}</caption>
            <thead>
              <tr className="bg-surface-sunk">
                {columns.map((column) => (
                  <th
                    key={column.key}
                    scope="col"
                    className={cn(
                      "px-4 py-3 type-label font-[650] whitespace-nowrap text-ink-muted",
                      column.align === "end" && "text-right",
                      column.showFrom && SHOW_FROM[column.showFrom],
                      column.className,
                    )}
                  >
                    {column.header}
                  </th>
                ))}
                {rowMenu && (
                  <th scope="col" className="w-16 px-4 py-3">
                    <span className="sr-only">{t("ui.actions")}</span>
                  </th>
                )}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={rowKey(row)}
                  className="border-t border-line transition-colors hover:bg-surface-sunk/40"
                >
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={cn(
                        "px-4 py-3.5 align-middle",
                        column.align === "end" && "text-right tabular-nums",
                        column.showFrom && SHOW_FROM[column.showFrom],
                        column.className,
                      )}
                    >
                      {column.cell(row)}
                    </td>
                  ))}
                  {rowMenu && <td className="px-4 py-2 text-right">{rowMenu(row)}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      {footer}
    </div>
  );
}

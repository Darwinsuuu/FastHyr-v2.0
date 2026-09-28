"use client";

import { CaretLeftIcon, CaretRightIcon } from "@phosphor-icons/react";

import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";
import { t } from "@/lib/i18n";
import { pageWindow } from "@/lib/pagination";

export interface PaginationProps {
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
  pageSizes?: number[];
  /** What the rows are, already pluralised for `total`, e.g. "pipelines". */
  noun: string;
  className?: string;
}

/** Up to 5 page numbers around the current one. */
function visiblePages(page: number, pageCount: number): number[] {
  const start = Math.max(1, Math.min(page - 2, pageCount - 4));
  return Array.from({ length: Math.min(5, pageCount) }, (_, index) => start + index);
}

const navButton = cn(
  "inline-flex h-10 min-w-10 items-center justify-center gap-1 rounded-[10px] border bg-surface-raised px-3 text-[14px] font-semibold",
  "border-line-strong text-ink hover:border-ink disabled:cursor-not-allowed disabled:border-line disabled:text-ink-muted disabled:opacity-70",
);

/**
 * "Showing 1–10 of 42 pipelines", rows per page and page buttons. On phones: Prev, "Page 2 of 9", Next.
 * Out-of-range pages clamp to the ends.
 */
export function Pagination({
  total,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
  pageSizes = [5, 10, 25],
  noun,
  className,
}: PaginationProps) {
  const window = pageWindow(total, page, pageSize);
  const go = (next: number) => onPageChange(pageWindow(total, next, pageSize).page);

  return (
    <nav
      aria-label={t("ui.pagination")}
      className={cn(
        "flex flex-col gap-3 border-t border-line px-4 py-3 text-[14px] text-ink-muted md:flex-row md:items-center md:justify-between md:px-5",
        className,
      )}
    >
      <p className="hidden md:block" aria-live="polite">
        {t("ui.showing", {
          from: formatNumber(window.from),
          to: formatNumber(window.to),
          total: formatNumber(total),
          noun,
        })}
      </p>
      <div className="flex items-center justify-between gap-5 md:justify-end">
        {onPageSizeChange && (
          <label className="hidden items-center gap-2 md:flex">
            {t("ui.rowsPerPage")}
            <select
              value={pageSize}
              onChange={(event) => onPageSizeChange(Number(event.target.value))}
              className="h-10 rounded-[10px] border border-line-strong bg-surface-raised px-3 text-[14px] text-ink"
            >
              {pageSizes.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </label>
        )}
        <div className="flex w-full items-center justify-between gap-1.5 md:w-auto">
          <button
            type="button"
            className={navButton}
            disabled={!window.hasPrevious}
            onClick={() => go(window.page - 1)}
          >
            <CaretLeftIcon aria-hidden="true" className="size-4" />
            {t("ui.previous")}
          </button>
          <span className="text-ink md:hidden" aria-live="polite">
            {t("ui.pageOf", { page: window.page, count: window.pageCount })}
          </span>
          <span className="hidden gap-1.5 md:flex">
            {visiblePages(window.page, window.pageCount).map((number) => (
              <button
                key={number}
                type="button"
                aria-label={t("ui.goToPage", { page: number })}
                aria-current={number === window.page ? "page" : undefined}
                onClick={() => go(number)}
                className={cn(
                  navButton,
                  "px-0 font-[650] tabular-nums",
                  number === window.page
                    ? "border-evergreen bg-evergreen text-on-evergreen hover:border-evergreen"
                    : "border-line",
                )}
              >
                {number}
              </button>
            ))}
          </span>
          <button
            type="button"
            className={navButton}
            disabled={!window.hasNext}
            onClick={() => go(window.page + 1)}
          >
            {t("ui.next")}
            <CaretRightIcon aria-hidden="true" className="size-4" />
          </button>
        </div>
      </div>
    </nav>
  );
}

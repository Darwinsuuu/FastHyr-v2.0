export interface PageWindow {
  /** 1-based page, clamped into range. */
  page: number;
  pageCount: number;
  /** 1-based index of the first row shown, 0 when there are no rows. */
  from: number;
  /** 1-based index of the last row shown. */
  to: number;
  hasPrevious: boolean;
  hasNext: boolean;
}

/** Where a page sits in a list of `total` rows: "11–20 of 42". Out-of-range pages clamp to the ends. */
export function pageWindow(total: number, page: number, pageSize: number): PageWindow {
  const size = Math.max(1, Math.floor(pageSize));
  const pageCount = Math.max(1, Math.ceil(Math.max(0, total) / size));
  const current = Math.min(pageCount, Math.max(1, Math.floor(page) || 1));
  const from = total > 0 ? (current - 1) * size + 1 : 0;
  const to = Math.min(total, current * size);
  return {
    page: current,
    pageCount,
    from,
    to,
    hasPrevious: current > 1,
    hasNext: current < pageCount,
  };
}

/** Page after a rows-per-page change, kept so the first visible row stays on screen. */
export function pageAfterResize(page: number, oldSize: number, newSize: number): number {
  const firstRow = (Math.max(1, page) - 1) * oldSize;
  return Math.floor(firstRow / newSize) + 1;
}

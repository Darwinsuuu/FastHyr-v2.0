// Locale-aware formatting. Dates and times are shown in the workspace's time zone
// (BACKEND.md §3: stored in UTC, converted only for display).

type DateInput = Date | string | number;

const toDate = (value: DateInput) => (value instanceof Date ? value : new Date(value));

/** "28 Sept 2026" in en-GB, "Sep 28, 2026" in en-US. */
export function formatDate(value: DateInput, timeZone: string, locale?: string): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone }).format(toDate(value));
}

/** "2:30 pm" / "2:30 PM", in the workspace time zone. */
export function formatTime(value: DateInput, timeZone: string, locale?: string): string {
  return new Intl.DateTimeFormat(locale, { timeStyle: "short", timeZone }).format(toDate(value));
}

export function formatDateTime(value: DateInput, timeZone: string, locale?: string): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone,
  }).format(toDate(value));
}

export function formatNumber(value: number, locale?: string): string {
  return new Intl.NumberFormat(locale).format(value);
}

/** Money is integer cents plus an ISO currency (BACKEND.md §3). */
export function formatMoney(cents: number, currency: string, locale?: string): string {
  return new Intl.NumberFormat(locale, { style: "currency", currency }).format(cents / 100);
}

/** File sizes in binary units, e.g. 10485760 → "10 MB". */
export function formatBytes(bytes: number, locale?: string): string {
  const units = ["bytes", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const digits = unit === 0 || value >= 10 ? 0 : 1;
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(value)} ${units[unit]}`;
}

/** "Thu, 31 Dec 2026" in en-GB: a date someone plans around, such as a pipeline's close date. */
export function formatDayLong(value: DateInput, timeZone?: string, locale?: string): string {
  return new Intl.DateTimeFormat(locale, {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone,
  }).format(toDate(value));
}

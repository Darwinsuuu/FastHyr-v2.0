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

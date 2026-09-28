import { describe, expect, it } from "vitest";

import { formatDate, formatDateTime, formatMoney, formatTime } from "./index";

// 23:30 UTC on 28 September is already 29 September in Manila and still the 28th in New York.
const LATE_EVENING_UTC = "2026-09-28T23:30:00Z";

describe("dates in the workspace time zone", () => {
  it("shows the calendar day of the workspace, not UTC", () => {
    expect(formatDate(LATE_EVENING_UTC, "Asia/Manila", "en-GB")).toBe("29 Sept 2026");
    expect(formatDate(LATE_EVENING_UTC, "America/New_York", "en-GB")).toBe("28 Sept 2026");
  });

  it("shows the local time of the workspace", () => {
    expect(formatTime(LATE_EVENING_UTC, "Asia/Manila", "en-US")).toBe("7:30 AM");
    expect(formatTime(LATE_EVENING_UTC, "UTC", "en-GB")).toBe("23:30");
  });

  it("combines date and time", () => {
    expect(formatDateTime(LATE_EVENING_UTC, "Asia/Manila", "en-US")).toBe("Sep 29, 2026, 7:30 AM");
  });
});

describe("money", () => {
  it("formats integer cents with the currency", () => {
    expect(formatMoney(129900, "USD", "en-US")).toBe("$1,299.00");
  });
});

import { describe, expect, it } from "vitest";

import {
  creditTone,
  menuForRole,
  type PipelineListItem,
  remaining,
  shortDate,
} from "@/lib/pipelines/list";
import { can } from "@/lib/permissions";

const MANILA = "Asia/Manila";
// Saturday 10 October 2026, 9:00 in Manila.
const NOW = new Date("2026-10-10T01:00:00Z");

function item(change: Partial<PipelineListItem>): PipelineListItem {
  return {
    id: "p1",
    status: "live",
    closed_reason: null,
    title: "Data Analyst",
    slug: "data-analyst",
    department: null,
    owner: null,
    candidates: 0,
    to_review: 0,
    credits_used: 0,
    credits_reserved: 100,
    opens_at: null,
    closes_at: null,
    ended_at: null,
    updated_at: NOW.toISOString(),
    ...change,
  };
}

describe("remaining", () => {
  it("counts calendar days in the workspace's time zone", () => {
    // 23:30 on the 11th in Manila is still one day away, though under 24 hours in UTC terms.
    const closes = "2026-10-11T15:30:00Z";
    expect(remaining(item({ closes_at: closes }), NOW, MANILA)).toEqual({
      label: "1 day left",
      emphasis: "soon",
    });
    expect(remaining(item({ closes_at: "2026-10-10T15:00:00Z" }), NOW, MANILA).label).toBe(
      "Closes today",
    );
  });

  it("shows soon only for live pipelines, and out of credits as blocked", () => {
    const closes = "2026-12-20T00:00:00Z";
    expect(remaining(item({ closes_at: closes }), NOW, MANILA)).toEqual({
      label: "71 days left",
      emphasis: "normal",
    });
    const paused = item({ status: "paused_no_credits", closes_at: "2026-10-15T00:00:00Z" });
    expect(remaining(paused, NOW, MANILA).emphasis).toBe("blocked");
  });

  it("says when scheduled pipelines open and when ended ones ended", () => {
    const scheduled = (opens_at: string) =>
      remaining(item({ status: "scheduled", opens_at }), NOW, MANILA).label;
    expect(scheduled("2026-10-11T00:00:00Z")).toBe("Opens tomorrow");
    expect(scheduled("2026-10-13T00:00:00Z")).toBe("Opens in 3 days");
    const ended = { ended_at: "2026-09-02T04:00:00Z" };
    expect(remaining(item({ status: "closed", ...ended }), NOW, MANILA).label).toBe("Closed 2 Sep");
    expect(remaining(item({ status: "cancelled", ...ended }), NOW, MANILA).label).toBe(
      "Cancelled 2 Sep",
    );
    expect(remaining(item({ status: "draft" }), NOW, MANILA).label).toBe("Not published");
  });
});

it("adds the year to dates from another year", () => {
  expect(shortDate(new Date("2025-08-18T04:00:00Z"), NOW, MANILA)).toBe("18 Aug 2025");
});

it("colours the credit bar by how much of the reserve is used", () => {
  expect(creditTone(item({ credits_used: 79 }))).toBe("normal");
  expect(creditTone(item({ credits_used: 80 }))).toBe("low");
  expect(creditTone(item({ credits_used: 100 }))).toBe("out");
  expect(creditTone(item({ status: "closed", credits_used: 100 }))).toBe("muted");
});

describe("menuForRole", () => {
  it("gives Admins every action for the status", () => {
    expect(menuForRole("live", (action) => can("admin", action))).toEqual([
      "open",
      "copyLink",
      "viewSetup",
      "separator",
      "pause",
      "close",
    ]);
  });

  it("leaves Hiring managers only what they can see, without stray separators", () => {
    const allowed = (action: Parameters<typeof can>[1]) => can("hiring_manager", action);
    expect(menuForRole("live", allowed)).toEqual(["open", "copyLink", "viewSetup"]);
    expect(menuForRole("closed", allowed)).toEqual(["viewResults"]);
    expect(menuForRole("draft", allowed)).toEqual([]);
  });
});

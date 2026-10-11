import { describe, expect, it } from "vitest";

import {
  dayLabel,
  dropRows,
  dropTotal,
  funnelRows,
  longDate,
  medianDays,
  openedLabel,
  type PipelineDashboard,
  type PipelineDetail,
  parseTab,
  scoreHistogram,
  sourceLabel,
  tabHref,
  weekdayDate,
} from "@/lib/pipelines/detail";

const bins = (counts: number[]): PipelineDashboard["scores"] =>
  counts.map((count, index) => ({ start: index * 10, count }));

const dropoffs = {
  link_expired: 3,
  left_unfinished: 2,
  technical_issue: 1,
  invited: 58,
  reinvitable: 6,
};

describe("tabs", () => {
  it("falls back to the Dashboard and keeps other tabs in the URL", () => {
    expect(parseTab("candidates")).toBe("candidates");
    expect(parseTab("nope")).toBe("dashboard");
    expect(parseTab(null)).toBe("dashboard");
    expect(tabHref("p1", "dashboard")).toBe("/pipelines/p1");
    expect(tabHref("p1", "setup")).toBe("/pipelines/p1?tab=setup");
  });
});

describe("dates", () => {
  it("writes dates in the workspace's time zone, day first", () => {
    const value = new Date("2026-09-30T18:00:00Z"); // 1 Oct in Manila
    expect(longDate(value, "Asia/Manila")).toBe("1 Oct 2026");
    expect(longDate(value, "UTC")).toBe("30 Sep 2026");
    expect(weekdayDate(new Date("2027-02-26T03:00:00Z"), "Asia/Manila")).toBe("Fri, 26 Feb 2027");
    expect(dayLabel("2026-09-29")).toBe("29 Sep");
  });

  it("says when a pipeline opened, or when it will", () => {
    const pipeline = (status: PipelineDetail["status"]) =>
      ({ status, opens_at: "2026-07-21T01:00:00Z" }) as PipelineDetail;
    expect(openedLabel(pipeline("live"), "UTC")).toBe("Opened 21 Jul 2026");
    expect(openedLabel(pipeline("scheduled"), "UTC")).toBe("Opens 21 Jul 2026");
    expect(openedLabel(pipeline("draft"), "UTC")).toBeNull();
  });
});

describe("medianDays", () => {
  it("rounds to a tenth and has nothing without assessments", () => {
    expect(medianDays(1.64)).toBe("1.6");
    expect(medianDays(0.01)).toBe("under 0.1");
    expect(medianDays(null)).toBeNull();
  });
});

describe("funnelRows", () => {
  it("gives each stage as a share of the step before, flagged counted with ready", () => {
    const rows = funnelRows({
      applied: 142,
      invited: 58,
      interviewed: 35,
      ready_for_review: 4,
      flagged: 2,
    });
    expect(rows.map((row) => [row.value, row.rate])).toEqual([
      [142, ""],
      [58, "41%"],
      [35, "60%"],
      [6, "17%"],
    ]);
  });

  it("leaves the rate out when the step before is empty", () => {
    const rows = funnelRows({
      applied: 0,
      invited: 0,
      interviewed: 0,
      ready_for_review: 0,
      flagged: 0,
    });
    expect(rows.map((row) => row.rate)).toEqual(["", "", "", ""]);
  });
});

describe("scoreHistogram", () => {
  it("starts at the lowest score and marks bands from the pass mark", () => {
    const histogram = scoreHistogram(bins([0, 0, 0, 0, 5, 10, 14, 3, 2, 1]), 70);
    expect(histogram.bins.map((bin) => bin.label)).toEqual([
      "40s",
      "50s",
      "60s",
      "70s",
      "80s",
      "90+",
    ]);
    expect(histogram.bins.map((bin) => bin.passing)).toEqual([
      false,
      false,
      false,
      true,
      true,
      true,
    ]);
    expect(histogram.passIndex).toBe(3);
  });

  it("keeps the pass mark's band in view when every score is above it", () => {
    const histogram = scoreHistogram(bins([0, 0, 0, 0, 0, 0, 0, 0, 2, 1]), 75);
    expect(histogram.bins.map((bin) => bin.label)).toEqual(["70s", "80s", "90+"]);
    expect(histogram.passIndex).toBe(0);
  });

  it("labels the lowest band", () => {
    const histogram = scoreHistogram(bins([1, 0, 0, 0, 0, 0, 0, 0, 0, 0]), 100);
    expect(histogram.bins[0]?.label).toBe("0–9");
    expect(histogram.bins.at(-1)?.passing).toBe(true);
  });
});

describe("sources and drop-offs", () => {
  it("names sources from the apply link tag", () => {
    expect(sourceLabel("linkedin")).toBe("LinkedIn");
    expect(sourceLabel("careers")).toBe("Careers page");
    expect(sourceLabel("direct")).toBe("Direct link");
  });

  it("lists every reason with the pipeline's link expiry", () => {
    const rows = dropRows(dropoffs, 5);
    expect(rows.map((row) => [row.label, row.count])).toEqual([
      ["Link expired", 3],
      ["Left mid-interview", 2],
      ["Technical issue", 1],
    ]);
    expect(rows[0]?.description).toBe("Didn't start within 5 days");
    expect(dropTotal(dropoffs)).toBe(6);
  });
});

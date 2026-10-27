import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { can } from "@/lib/permissions";
import {
  dialogFacts,
  failureMessage,
  headerMenuFor,
  pausePoints,
  type PipelineSummary,
  successMessage,
} from "@/lib/pipelines/actions";

const MANILA = "Asia/Manila";
// Saturday 10 October 2026, 9:00 in Manila.
const NOW = new Date("2026-10-10T01:00:00Z");

function summary(change: Partial<PipelineSummary>): PipelineSummary {
  return {
    id: "p1",
    title: "Data Analyst",
    status: "live",
    closed_reason: null,
    candidates: 48,
    to_review: 6,
    credits_used: 48,
    credits_reserved: 100,
    opens_at: "2026-09-01T01:00:00Z",
    closes_at: "2026-10-22T15:59:59Z",
    ended_at: null,
    ...change,
  };
}

const admin = (action: Parameters<typeof can>[1]) => can("admin", action);

describe("dialogFacts", () => {
  it("shows who applied, who waits and the days that were left when closing", () => {
    expect(dialogFacts("close", summary({}), NOW, MANILA)).toEqual([
      { label: "Candidates who applied", value: "48" },
      { label: "Still waiting on your review", value: "6" },
      { label: "Days that were left", value: "12" },
    ]);
  });

  it("returns the whole reserve when a scheduled pipeline is cancelled", () => {
    const scheduled = summary({
      status: "scheduled",
      credits_used: 0,
      credits_reserved: 150,
      opens_at: "2026-10-14T16:00:00Z",
    });
    expect(dialogFacts("cancel", scheduled, NOW, MANILA)).toEqual([
      { label: "Was going to open", value: "15 Oct 2026" },
      { label: "Credits returned", value: "150" },
    ]);
  });

  it("shows when an archived pipeline ended", () => {
    const closed = summary({ status: "closed", ended_at: "2026-09-02T04:00:00Z" });
    expect(dialogFacts("archive", closed, NOW, MANILA)).toEqual([
      { label: "Candidates", value: "48" },
      { label: "Status", value: "Closed 2 Sep" },
    ]);
  });
});

describe("pausePoints", () => {
  it("says the countdown keeps going and counts who carries on", () => {
    expect(pausePoints(summary({ candidates: 1 }), NOW, MANILA)).toEqual({
      countdown: "This pipeline still closes on schedule (12 days left), paused or not.",
      carryOn: "The 1 person who already applied can still finish their interview.",
    });
  });
});

describe("successMessage", () => {
  it("says how many candidates hear the role closed", () => {
    expect(successMessage("close", summary({}), { status: "closed", notified: 3 })).toBe(
      "Data Analyst is closed. We're letting 3 candidates know.",
    );
    expect(successMessage("close", summary({}), { status: "closed", notified: 0 })).toBe(
      "Data Analyst is closed",
    );
  });

  it("explains a resume that stays paused for credits", () => {
    expect(successMessage("resume", summary({}), { status: "paused_no_credits" })).toBe(
      "Data Analyst is out of credits, so it stays paused",
    );
  });
});

describe("failureMessage", () => {
  it("tells apart a pipeline that moved on from other failures", () => {
    expect(failureMessage(new ApiError(409, "invalid_transition", "Conflict"))).toMatch(
      /changed since the page loaded/,
    );
    expect(failureMessage(new Error("offline"))).toMatch(/Check your connection/);
  });
});

describe("headerMenuFor", () => {
  it("leaves out what opens this page and adds Duplicate before the lifecycle actions", () => {
    expect(headerMenuFor("live", false, admin)).toEqual([
      "copyLink",
      "duplicate",
      "separator",
      "pause",
      "close",
    ]);
    expect(headerMenuFor("closed", false, admin)).toEqual(["duplicate", "separator", "archive"]);
  });

  it("drops Archive once archived, and everything a Hiring manager can't do", () => {
    expect(headerMenuFor("closed", true, admin)).toEqual(["duplicate"]);
    const hiringManager = (action: Parameters<typeof can>[1]) => can("hiring_manager", action);
    expect(headerMenuFor("live", false, hiringManager)).toEqual(["copyLink"]);
  });
});

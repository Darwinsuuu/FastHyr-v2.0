import { describe, expect, it } from "vitest";

import { changeNote, type FlowSummary, flowStages, medianLabel } from "@/lib/pipelines/flow";

function flow(change: Partial<FlowSummary>): FlowSummary {
  return {
    period: { range: "week", start: "2026-10-03T01:00:00Z", end: "2026-10-10T01:00:00Z" },
    applied: 40,
    applied_change_pct: 18,
    processing: 3,
    invited: 30,
    not_a_match: 7,
    interviewed: 20,
    in_progress: 1,
    not_started: 9,
    scoring: 0,
    ready_for_review: 12,
    flagged: 1,
    did_not_pass: 0,
    median_hours_to_assessment: 30,
    ...change,
  };
}

describe("changeNote", () => {
  it("signs the change and leaves it out when nobody applied before", () => {
    expect(changeNote(18)).toBe("+18%");
    expect(changeNote(-9)).toBe("−9%");
    expect(changeNote(0)).toBe("0%");
    expect(changeNote(null)).toBeUndefined();
  });
});

describe("flowStages", () => {
  it("shows each stage's share of the one before and what sits beside it", () => {
    const [applied, invited, interviewed, ready] = flowStages(flow({}));
    expect(applied).toMatchObject({ value: 40, note: "+18%" });
    expect(applied?.detail).toBe("vs last week · 3 still processing résumé");
    expect(invited).toMatchObject({ value: 30, note: "75%", detail: "7 résumés not a match" });
    expect(interviewed).toMatchObject({ value: 20, note: "67%" });
    expect(interviewed?.detail).toBe("1 interview in progress · 9 not started yet");
    expect(ready).toMatchObject({ value: 12, attention: true, detail: "Plus 1 flagged" });
  });

  it("drops empty details and shares when there is nothing to divide by", () => {
    const [applied, invited, , ready] = flowStages(
      flow({
        applied: 0,
        applied_change_pct: null,
        processing: 0,
        invited: 0,
        not_a_match: 0,
        flagged: 0,
        did_not_pass: 2,
      }),
    );
    expect(applied?.note).toBeUndefined();
    expect(applied?.detail).toBeUndefined();
    expect(invited?.note).toBeUndefined();
    expect(ready?.detail).toBe("2 didn't pass interview");
  });

  it("names the 30-day comparison", () => {
    const [applied] = flowStages(
      flow({
        period: { range: "30d", start: "2026-09-10T01:00:00Z", end: "2026-10-10T01:00:00Z" },
      }),
    );
    expect(applied?.detail).toContain("vs previous 30 days");
  });
});

describe("medianLabel", () => {
  it("uses hours under a day and days with one decimal after", () => {
    expect(medianLabel(null)).toBeNull();
    expect(medianLabel(0.2)).toBe("1 hour");
    expect(medianLabel(14.4)).toBe("14 hours");
    expect(medianLabel(43)).toBe("1.8 days");
    expect(medianLabel(24)).toBe("1 day");
  });
});

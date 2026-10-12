import { describe, expect, it } from "vitest";

import {
  type ApplicationProfile,
  citations,
  clock,
  confidenceWord,
  delay,
  distributionBins,
  historyChange,
  hoursToAssessment,
  integrityRows,
  integritySummary,
  ordinal,
  parseProfileTab,
  parseSeek,
  type ProfileAssessment,
  type ProfileFlag,
  type ProfileIntegrity,
  profileActions,
  profileHref,
  scoreSentence,
} from "@/lib/candidates/profile";

const assessment = (overrides: Partial<ProfileAssessment> = {}): ProfileAssessment =>
  ({
    overall_score: 91,
    passed: true,
    fit: "strong",
    pass_mark: 70,
    assessed_at: "2026-09-23T03:00:00Z",
    ...overrides,
  }) as ProfileAssessment;

const profile = (overrides: Partial<ApplicationProfile> = {}): ApplicationProfile =>
  ({
    id: "app-1",
    stage: "ready_for_review",
    flagged: false,
    open_flags: 0,
    applied_at: "2026-09-22T01:00:00Z",
    resume: {
      must_haves: [
        { name: "Python", met: true },
        { name: "SQL", met: true },
        { name: "English", met: true },
      ],
    },
    assessment: assessment(),
    integrity: null,
    history: [],
    ...overrides,
  }) as ApplicationProfile;

const flag = (overrides: Partial<ProfileFlag> = {}): ProfileFlag => ({
  id: "flag-1",
  type: "read_aloud",
  start_ms: 190_000,
  end_ms: 220_000,
  confidence: 0.7,
  status: "open",
  ...overrides,
});

describe("profile URL", () => {
  it("names the application, the tab and a moment by ID and seconds only", () => {
    expect(profileHref("cand-1", "app-1")).toBe("/candidates/cand-1?application=app-1");
    expect(profileHref("cand-1", "app-1", "resume")).toBe(
      "/candidates/cand-1?application=app-1&tab=resume",
    );
    expect(profileHref("cand-1", "app-1", "interview", 201.9)).toBe(
      "/candidates/cand-1?application=app-1&tab=interview&t=201",
    );
    // A moment only belongs to the recording.
    expect(profileHref("cand-1", "app-1", "resume", 30)).not.toContain("t=");
  });

  it("reads the tab and the moment back safely", () => {
    expect(parseProfileTab("interview")).toBe("interview");
    expect(parseProfileTab("scores")).toBe("overview");
    expect(parseProfileTab(null)).toBe("overview");
    expect(parseSeek("201")).toBe(201);
    expect(parseSeek("-3")).toBeNull();
    expect(parseSeek("1e3")).toBeNull();
    expect(parseSeek(null)).toBeNull();
  });
});

describe("formatting", () => {
  it("writes times, delays and ordinals", () => {
    expect(clock(201_000)).toBe("3:21");
    expect(clock(3_725_000)).toBe("1:02:05");
    expect(clock(-5)).toBe("0:00");
    expect(delay(2_140)).toBe("2.1s");
    expect([1, 2, 3, 4, 11, 12, 13, 21, 22, 103].map(ordinal)).toEqual([
      "1st",
      "2nd",
      "3rd",
      "4th",
      "11th",
      "12th",
      "13th",
      "21st",
      "22nd",
      "103rd",
    ]);
  });

  it("sums up the score against the pass mark and must-haves", () => {
    const strong = profile();
    expect(scoreSentence(strong, assessment())).toBe(
      "Strong fit. Scored 21 points above your pass mark and meets all 3 must-haves.",
    );
    const below = profile({
      resume: {
        ...strong.resume,
        must_haves: [
          { name: "Python", met: true },
          { name: "SQL", met: false },
        ],
      },
    });
    expect(scoreSentence(below, assessment({ overall_score: 69, passed: false, fit: null }))).toBe(
      "Didn't pass. Scored 1 point below your pass mark and meets 1 of 2 must-haves.",
    );
  });

  it("splits summary citations from the text", () => {
    expect(citations("Clear on APIs [1] and testing [2].")).toEqual([
      { text: "Clear on APIs" },
      { ref: 1 },
      { text: " and testing" },
      { ref: 2 },
      { text: "." },
    ]);
    expect(citations("No references.")).toEqual([{ text: "No references." }]);
  });
});

describe("comparisons", () => {
  const distribution = [0, 50, 60, 70, 80, 90].map((start) => ({ start, count: start / 10 }));

  it("labels the groups and marks the candidate's own and the passing ones", () => {
    const bins = distributionBins(distribution, 91, 70);
    expect(bins.map((bin) => bin.label)).toEqual(["<50", "50s", "60s", "70s", "80s", "90+"]);
    expect(bins.filter((bin) => bin.own).map((bin) => bin.label)).toEqual(["90+"]);
    expect(bins.filter((bin) => bin.passing).map((bin) => bin.label)).toEqual([
      "70s",
      "80s",
      "90+",
    ]);
    expect(distributionBins(distribution, 100, 95).find((bin) => bin.own)?.label).toBe("90+");
    expect(distributionBins(distribution, 12, 70).find((bin) => bin.own)?.label).toBe("<50");
  });

  it("measures the change across the person's scored applications", () => {
    const item = (overall_score: number | null) =>
      ({ overall_score }) as ApplicationProfile["history"][number];
    expect(historyChange([item(49), item(null), item(76)])).toBe(27);
    expect(historyChange([item(80)])).toBeNull();
  });

  it("counts the hours from applying to the assessment", () => {
    expect(hoursToAssessment(profile())).toBe(26);
    expect(hoursToAssessment(profile({ assessment: null }))).toBeNull();
  });
});

describe("integrity", () => {
  const ran = { face: "ran", second_voice: "ran", timing: "ran", read_aloud: "ran" } as const;
  const integrity = (overrides: Partial<ProfileIntegrity> = {}): ProfileIntegrity => ({
    status: "ready",
    checks: ran,
    flags: [],
    ...overrides,
  });

  it("says confidence in words, never as a number", () => {
    expect(confidenceWord(0.8)).toBe("Likely");
    expect(confidenceWord(0.79)).toBe("Possible");
  });

  it("gives each check a state and the reason one didn't run", () => {
    const rows = integrityRows(
      integrity({
        checks: { ...ran, face: "voice_only" },
        flags: [flag(), flag({ id: "flag-2", type: "second_voice", status: "no_concern" })],
      }),
    );
    expect(rows.map((row) => [row.key, row.state, row.reason ?? null])).toEqual([
      ["sameFace", "notRun", "Voice-only interview"],
      ["inFrame", "notRun", "Voice-only interview"],
      ["oneVoice", "reviewed", null],
      ["readAloud", "flagged", null],
      ["timing", "passed", null],
    ]);
  });

  it("sums the checks up for the score card", () => {
    expect(integritySummary(profile({ integrity: integrity() }))).toBe("All clear");
    expect(
      integritySummary(profile({ integrity: integrity({ flags: [flag()] }), open_flags: 1 })),
    ).toBe("1 flag to review");
    expect(integritySummary(profile({ integrity: integrity({ status: "off" }) }))).toBe(
      "Off for this pipeline",
    );
    expect(integritySummary(profile({ integrity: null }))).toBe("Not checked yet");
  });
});

describe("actions", () => {
  it("lets deciders advance from Ready for review only, and Hiring managers only read", () => {
    expect(profileActions(profile(), true)).toEqual({
      email: true,
      advance: true,
      reject: true,
      report: true,
    });
    expect(profileActions(profile({ flagged: true }), true).advance).toBe(false);
    expect(profileActions(profile({ stage: "advanced" }), true)).toMatchObject({
      advance: false,
      reject: false,
    });
    expect(profileActions(profile(), false)).toEqual({
      email: false,
      advance: false,
      reject: false,
      report: true,
    });
    expect(profileActions(profile({ assessment: null }), false).report).toBe(false);
  });
});

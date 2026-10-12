import { describe, expect, it } from "vitest";

import {
  appliedLabel,
  candidateActionHref,
  candidateMenu,
  candidatesHref,
  filtersFor,
  fitExplanation,
  parseFilter,
  type PipelineCandidate,
  type PipelineCandidates,
  shouldPoll,
} from "@/lib/pipelines/candidates";

const row = (overrides: Partial<PipelineCandidate> = {}): PipelineCandidate => ({
  id: "app-1",
  candidate: { id: "cand-1", name: "Bea Garcia", email: "bea@example.test" },
  stage: "ready_for_review",
  flagged: false,
  review_requested: false,
  fit: "strong",
  overall_score: 91,
  must_haves: { met: 4, total: 4 },
  strongest: "technical",
  flag_types: [],
  source: "linkedin",
  applied_at: "2026-09-22T01:14:00Z",
  ...overrides,
});

const counts = (overrides: Partial<PipelineCandidates["counts"]> = {}) => ({
  all: 10,
  processing: 0,
  not_a_match: 2,
  invited: 3,
  in_progress: 0,
  ready: 2,
  did_not_pass: 1,
  flagged: 1,
  review_requested: 0,
  advanced: 1,
  rejected: 0,
  ...overrides,
});

describe("filters", () => {
  it("gives Hiring managers the shortlist filters only", () => {
    expect(filtersFor(true)).toEqual(["all", "ready", "flagged", "advanced"]);
    expect(filtersFor(false)).toHaveLength(11);
  });

  it("reads ?stage= and falls back to All", () => {
    expect(parseFilter("flagged", false)).toBe("flagged");
    expect(parseFilter("invited", true)).toBe("all");
    expect(parseFilter("nope", false)).toBe("all");
    expect(parseFilter(null, false)).toBe("all");
  });

  it("links to a filter", () => {
    expect(candidatesHref("p1")).toBe("/pipelines/p1?tab=candidates");
    expect(candidatesHref("p1", "ready")).toBe("/pipelines/p1?tab=candidates&stage=ready");
  });

  it("polls only while someone is being screened, interviewed or scored", () => {
    expect(shouldPoll(counts())).toBe(false);
    expect(shouldPoll(counts({ processing: 1 }))).toBe(true);
    expect(shouldPoll(counts({ in_progress: 2 }))).toBe(true);
    expect(shouldPoll(undefined)).toBe(false);
  });
});

describe("appliedLabel", () => {
  it("writes the date and time in the workspace's time zone", () => {
    expect(appliedLabel("2026-09-22T01:14:00Z", "Asia/Manila")).toEqual({
      date: "22 Sep 2026",
      time: "9:14 AM",
    });
    expect(appliedLabel("2026-09-22T01:14:00Z", "America/New_York").date).toBe("21 Sep 2026");
  });
});

describe("fitExplanation", () => {
  it("explains a strong fit with the résumé and interview numbers", () => {
    expect(fitExplanation(row(), 70)).toEqual({
      label: "Strong fit",
      description:
        "Passed the AI interview with 80 or higher and meets every must-have. A good one to look at first.",
      why: "Résumé 4 of 4 must-haves · Interview 91/100. Strongest area: technical fit.",
    });
  });

  it("names the pass mark for a good fit", () => {
    const fit = fitExplanation(row({ fit: "good", overall_score: 74, must_haves: null }), 70);
    expect(fit?.description).toContain("your pass mark of 70");
    expect(fit?.why).toBe("Interview 74/100. Strongest area: technical fit.");
  });

  it("points a flagged candidate at the recording", () => {
    const fit = fitExplanation(
      row({ flagged: true, overall_score: 82, flag_types: ["second_voice", "read_aloud"] }),
      70,
    );
    expect(fit?.why).toBe(
      "Interview 82/100, but flagged: a second voice was heard; answers sounded read aloud. Review the recording before deciding.",
    );
  });

  it("shows nothing before a passed interview or once rejected", () => {
    expect(
      fitExplanation(row({ fit: null, stage: "invited", overall_score: null }), 70),
    ).toBeNull();
    expect(fitExplanation(row({ stage: "rejected" }), 70)).toBeNull();
  });
});

describe("candidateMenu", () => {
  const team = { decide: true, resolve: true };
  const hiringManager = { decide: false, resolve: false };

  it("offers advance and reject on a candidate ready for review", () => {
    expect(candidateMenu(row(), team)).toEqual([
      "profile",
      "resume",
      "report",
      "email",
      "separator",
      "advance",
      "reject",
    ]);
  });

  it("asks for the flag review before advancing a flagged candidate", () => {
    expect(candidateMenu(row({ flagged: true }), team)).toEqual([
      "profile",
      "resume",
      "report",
      "reviewFlag",
      "email",
      "separator",
      "reject",
    ]);
    // Didn't pass and flagged: nothing to decide from the list.
    expect(candidateMenu(row({ flagged: true, stage: "did_not_pass" }), team)).not.toContain(
      "reject",
    );
  });

  it("leaves out the report before an interview and decisions on finished stages", () => {
    const notAMatch = row({ stage: "resume_not_match", fit: null, overall_score: null });
    expect(candidateMenu(notAMatch, team)).toEqual(["profile", "resume", "email"]);
    expect(candidateMenu(row({ stage: "invited", overall_score: null }), team)).toEqual([
      "profile",
      "resume",
      "email",
      "separator",
      "reject",
    ]);
  });

  it("gives Hiring managers the profile and downloads only", () => {
    expect(candidateMenu(row({ flagged: true }), hiringManager)).toEqual([
      "profile",
      "resume",
      "report",
    ]);
  });

  it("only emails for now: the rest arrive with their own tasks", () => {
    expect(candidateActionHref("email", row())).toBe("mailto:bea@example.test");
    expect(candidateActionHref("advance", row())).toBeNull();
    expect(candidateActionHref("profile", row())).toBeNull();
  });
});

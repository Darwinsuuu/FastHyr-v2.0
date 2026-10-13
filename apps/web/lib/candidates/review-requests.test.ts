import { ApiError } from "@fasthyr/api-client";
import { describe, expect, it } from "vitest";

import {
  outcomeKey,
  type ProfileReviewRequest,
  resolutionBody,
  resolutionError,
  resolutionFailure,
  reviewOutcomes,
} from "@/lib/candidates/review-requests";

const request = (changes: Partial<ProfileReviewRequest> = {}): ProfileReviewRequest => ({
  id: "r1",
  decision_type: "resume",
  message: null,
  created_at: "2026-10-11T03:00:00Z",
  by_person: false,
  can_override: true,
  ...changes,
});

describe("review requests", () => {
  it("offers override only for an automated decision that still stands", () => {
    expect(reviewOutcomes(request())).toEqual(["uphold", "override"]);
    expect(reviewOutcomes(request({ by_person: true, can_override: false }))).toEqual(["uphold"]);
  });

  it("names the override by the decision it changes", () => {
    expect(outcomeKey(request(), "override")).toBe("invite");
    expect(outcomeKey(request({ decision_type: "interview" }), "override")).toBe("ready");
    expect(outcomeKey(request({ decision_type: "interview" }), "uphold")).toBe("uphold");
  });

  it("needs a note either way and trims it", () => {
    expect(resolutionError("  ")).toBe("Add a note so your team knows why.");
    expect(resolutionError("Looked again")).toBeNull();
    expect(resolutionBody("uphold", " Looked again ")).toEqual({
      outcome: "uphold",
      note: "Looked again",
    });
  });

  it("says why the API refused", () => {
    const refused = (status: number, code: string) => new ApiError(status, code, "No");
    expect(resolutionFailure(refused(409, "review_request_resolved"))).toMatch(/already resolved/);
    expect(resolutionFailure(refused(409, "override_not_allowed"))).toMatch(/only be upheld/);
    expect(resolutionFailure(refused(404, "not_found"))).toMatch(/isn't available/);
    expect(resolutionFailure(new Error("network"))).toBe("That didn't save. Try again.");
  });
});

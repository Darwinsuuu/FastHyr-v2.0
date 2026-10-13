import { ApiError } from "@fasthyr/api-client";
import { describe, expect, it } from "vitest";

import {
  advanceBody,
  decisionError,
  decisionFailure,
  EMPTY_DRAFT,
  rejectBody,
} from "@/lib/candidates/decisions";

describe("advance and reject", () => {
  it("needs a reason to reject but no note to advance", () => {
    expect(decisionError("reject", { text: "   ", email: true })).toBe(
      "Add a reason so your team knows why.",
    );
    expect(decisionError("reject", { text: "Needs Kubernetes", email: true })).toBeNull();
    expect(decisionError("advance", EMPTY_DRAFT)).toBeNull();
  });

  it("emails the candidate unless unticked and trims what the team wrote", () => {
    expect(EMPTY_DRAFT.email).toBe(true);
    expect(advanceBody({ text: "  ", email: true })).toEqual({ note: null, send_email: true });
    expect(advanceBody({ text: " Book a call ", email: false })).toEqual({
      note: "Book a call",
      send_email: false,
    });
    expect(rejectBody({ text: " Role filled ", email: true })).toEqual({
      reason: "Role filled",
      send_email: true,
    });
  });

  it("says why the API refused", () => {
    const refused = (status: number, code: string) => new ApiError(status, code, "No");
    expect(decisionFailure(refused(409, "flags_to_review"))).toBe(
      "Review this candidate's integrity flags before advancing them.",
    );
    expect(decisionFailure(refused(409, "decision_not_allowed"))).toMatch(/moved on/);
    expect(decisionFailure(refused(404, "not_found"))).toMatch(/isn't available/);
    expect(decisionFailure(new Error("network"))).toBe("That didn't save. Try again.");
  });
});

import { describe, expect, it } from "vitest";

import {
  draftFor,
  flagLabel,
  flagReviewBody,
  flagReviewErrors,
  flagSpan,
} from "@/lib/candidates/flags";
import type { ProfileFlag } from "@/lib/candidates/profile";

const flag = (overrides: Partial<ProfileFlag> = {}): ProfileFlag => ({
  id: "flag-1",
  type: "second_voice",
  start_ms: 252_000,
  end_ms: 260_000,
  confidence: 0.85,
  status: "open",
  resolved_at: null,
  resolved_by: null,
  note: null,
  ...overrides,
});

describe("flag review", () => {
  it("asks for a choice, and a note when a concern is confirmed", () => {
    expect(flagReviewErrors({ status: null, note: "" })).toEqual({
      status: "Choose No concern or Concern confirmed.",
    });
    expect(flagReviewErrors({ status: "no_concern", note: "" })).toEqual({});
    expect(flagReviewErrors({ status: "concern_confirmed", note: "   " })).toEqual({
      note: "Add a note saying what you saw or heard.",
    });
    expect(flagReviewErrors({ status: "concern_confirmed", note: "Someone spoke." })).toEqual({});
    expect(flagReviewErrors({ status: "no_concern", note: "x".repeat(1001) }).note).toBe(
      "Keep the note under 1000 characters.",
    );
  });

  it("sends the note trimmed, or none", () => {
    expect(flagReviewBody({ status: "no_concern", note: "  " })).toEqual({ status: "no_concern" });
    expect(flagReviewBody({ status: "concern_confirmed", note: " Read notes. " })).toEqual({
      status: "concern_confirmed",
      note: "Read notes.",
    });
  });

  it("starts an open flag empty and a reviewed one from its review", () => {
    expect(draftFor(flag())).toEqual({ status: null, note: "" });
    expect(
      draftFor(flag({ status: "concern_confirmed", note: "Read notes.", resolved_at: "x" })),
    ).toEqual({ status: "concern_confirmed", note: "Read notes." });
  });

  it("names the flag and its moment", () => {
    expect(flagLabel(flag())).toBe("A second voice");
    expect(flagSpan(flag())).toBe("4:12–4:20");
    expect(flagSpan(flag({ end_ms: 252_400 }))).toBe("4:12");
  });
});

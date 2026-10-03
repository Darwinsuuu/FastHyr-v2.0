import { describe, expect, it } from "vitest";

import {
  accommodationHref,
  interviewPath,
  isInterviewPath,
  readSignInProblem,
} from "@/lib/interview";

describe("isInterviewPath", () => {
  it("accepts an interview link on this site, with or without a query", () => {
    expect(isInterviewPath(interviewPath("abc_DEF-123"))).toBe(true);
    expect(isInterviewPath("/interview/abc?signin=cancelled")).toBe(true);
  });

  it("refuses anything that could leave the page", () => {
    for (const next of [
      null,
      "",
      "/interview/",
      "/interview/a/b",
      "//evil.example/interview/a",
      "https://evil.example/interview/a",
      "/interview/a\\b",
      "/apply/acme/role",
    ]) {
      expect(isInterviewPath(next)).toBe(false);
    }
  });
});

describe("readSignInProblem", () => {
  it("reads only the two problems the callback sends", () => {
    expect(readSignInProblem("cancelled")).toBe("cancelled");
    expect(readSignInProblem(["failed", "x"])).toBe("failed");
    expect(readSignInProblem("other")).toBeNull();
    expect(readSignInProblem(undefined)).toBeNull();
  });
});

describe("accommodationHref", () => {
  const company = { name: "Acme", logo_url: null, website: null, careers_url: null };

  it("prefers the careers page, then the website, else no link", () => {
    expect(
      accommodationHref({
        ...company,
        website: "https://acme.test",
        careers_url: "https://acme.test/jobs",
      }),
    ).toBe("https://acme.test/jobs");
    expect(accommodationHref({ ...company, website: "https://acme.test" })).toBe(
      "https://acme.test",
    );
    expect(accommodationHref(company)).toBeNull();
  });
});

import { describe, expect, it } from "vitest";

import {
  applyReturnPath,
  applySignInProblemPath,
  candidateFromClaims,
  isApplyPath,
  readReturn,
  withoutReturnParams,
} from "@/lib/apply/session";

describe("candidateFromClaims", () => {
  const google = {
    sub: "user-1",
    email: "paolo.reyes@gmail.com",
    app_metadata: { provider: "google", providers: ["google"] },
    user_metadata: { full_name: "Paolo Reyes" },
  };

  it("reads a Google or Microsoft session", () => {
    expect(candidateFromClaims(google)).toEqual({
      id: "user-1",
      name: "Paolo Reyes",
      email: "paolo.reyes@gmail.com",
      provider: "google",
    });
    expect(
      candidateFromClaims({
        ...google,
        app_metadata: { provider: "azure", providers: ["azure"] },
        user_metadata: { name: "Paolo" },
      }),
    ).toMatchObject({ provider: "azure", name: "Paolo" });
  });

  it("counts an account that also has Google linked", () => {
    expect(
      candidateFromClaims({
        ...google,
        app_metadata: { provider: "email", providers: ["email", "google"] },
      }),
    ).toMatchObject({ provider: "google" });
  });

  it("falls back to the email when the provider gave no name", () => {
    expect(candidateFromClaims({ ...google, user_metadata: {} })?.name).toBe(
      "paolo.reyes@gmail.com",
    );
  });

  it("treats no session and email + password sessions as signed out (ADR-014)", () => {
    expect(candidateFromClaims(null)).toBeNull();
    expect(candidateFromClaims(undefined)).toBeNull();
    expect(
      candidateFromClaims({ ...google, app_metadata: { provider: "email", providers: ["email"] } }),
    ).toBeNull();
    expect(candidateFromClaims({ ...google, email: undefined })).toBeNull();
  });
});

describe("applyReturnPath", () => {
  it("opens the form after sign-in from Apply now and keeps the source tag", () => {
    expect(
      applyReturnPath("acme-talent", "senior-backend-engineer", {
        intent: "apply",
        source: "linkedin",
      }),
    ).toBe("/apply/acme-talent/senior-backend-engineer?apply=1&source=linkedin");
  });

  it("only returns to the page from the header's Sign in, and leaves out a direct visit", () => {
    expect(applyReturnPath("acme-talent", "designer", { intent: "browse", source: "direct" })).toBe(
      "/apply/acme-talent/designer",
    );
  });

  it("is an apply path the callback accepts", () => {
    expect(isApplyPath(applyReturnPath("a", "b", { intent: "apply", source: "careers" }))).toBe(
      true,
    );
  });
});

describe("isApplyPath", () => {
  it("accepts apply pages, with or without a query", () => {
    expect(isApplyPath("/apply/acme-talent/designer")).toBe(true);
    expect(isApplyPath("/apply/acme-talent/designer?apply=1&source=indeed")).toBe(true);
  });

  it("rejects other paths and anything that could leave the site", () => {
    for (const next of [
      null,
      "",
      "/pipelines",
      "/apply/acme-talent",
      "/apply/acme-talent/designer/extra",
      "//evil.example/apply/a/b",
      "https://evil.example/apply/a/b",
      "/apply/a\\b/c",
      "/apply/a/b#x",
    ]) {
      expect(isApplyPath(next)).toBe(false);
    }
  });
});

describe("applySignInProblemPath", () => {
  it("returns to the page with the problem and keeps the intent and source", () => {
    expect(applySignInProblemPath("/apply/a/b?apply=1&source=linkedin", "cancelled")).toBe(
      "/apply/a/b?apply=1&source=linkedin&signin=cancelled",
    );
    expect(applySignInProblemPath("/apply/a/b", "failed")).toBe("/apply/a/b?signin=failed");
  });
});

describe("readReturn", () => {
  const params = (query: string) => new URLSearchParams(query);

  it("opens the form when a candidate comes back with the apply intent", () => {
    expect(readReturn(params("apply=1&source=linkedin"), true)).toEqual({
      openForm: true,
      problem: null,
      intent: "apply",
      clean: true,
    });
  });

  it("reopens sign-in with the problem when there's no session", () => {
    expect(readReturn(params("apply=1&signin=cancelled"), false)).toEqual({
      openForm: false,
      problem: "cancelled",
      intent: "apply",
      clean: true,
    });
    expect(readReturn(params("signin=failed"), false)).toMatchObject({
      problem: "failed",
      intent: "browse",
    });
  });

  it("does nothing on a plain visit, and ignores unknown values", () => {
    expect(readReturn(params("source=linkedin"), true)).toMatchObject({
      openForm: false,
      problem: null,
      clean: false,
    });
    expect(readReturn(params("signin=other"), false).problem).toBeNull();
    // Signed out with the apply intent (e.g. a shared link): nothing opens by itself.
    expect(readReturn(params("apply=1"), false).openForm).toBe(false);
  });
});

describe("withoutReturnParams", () => {
  it("drops the round trip's parameters and keeps the source tag", () => {
    expect(
      withoutReturnParams(
        "/apply/a/b",
        new URLSearchParams("apply=1&source=linkedin&signin=failed"),
      ),
    ).toBe("/apply/a/b?source=linkedin");
    expect(withoutReturnParams("/apply/a/b", new URLSearchParams("apply=1"))).toBe("/apply/a/b");
  });
});

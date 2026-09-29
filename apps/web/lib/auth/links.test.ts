import { describe, expect, it } from "vitest";

import { confirmDestination, verifyEmailRedirect } from "@/lib/auth/links";

describe("verifyEmailRedirect", () => {
  it("always has a query string, since the email template appends &token_hash=…", () => {
    expect(verifyEmailRedirect(null)).toBe("http://fasthyr.localhost:3000/auth/confirm?next=");
    expect(verifyEmailRedirect("/pipelines?tab=live")).toBe(
      "http://fasthyr.localhost:3000/auth/confirm?next=%2Fpipelines%3Ftab%3Dlive",
    );
  });
});

describe("confirmDestination", () => {
  const continueTo = "/auth/continue?next=%2Fpipelines";

  it("sends a verified reset link to the new-password page, a failed one to its expired state", () => {
    expect(confirmDestination({ type: "recovery", verified: true, continueTo })).toBe(
      "/reset-password",
    );
    expect(confirmDestination({ type: "recovery", verified: false, continueTo })).toBe(
      "/reset-password?error=link-expired",
    );
  });

  it("continues after email verification, or explains a used link on the login page", () => {
    expect(confirmDestination({ type: "email", verified: true, continueTo })).toBe(continueTo);
    expect(confirmDestination({ type: "email", verified: false, continueTo })).toBe(
      "/login?error=link-expired",
    );
    expect(confirmDestination({ type: null, verified: false, continueTo })).toBe(
      "/login?error=link-expired",
    );
  });
});

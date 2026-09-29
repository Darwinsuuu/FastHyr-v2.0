import { ApiError } from "@fasthyr/api-client";
import { describe, expect, it } from "vitest";

import {
  expiresSoon,
  expiryText,
  inviteActionErrorKey,
  inviteFormError,
  isEmail,
  sentText,
  shareMessage,
} from "./index";

const NOW = new Date("2026-09-29T12:00:00Z");
const ago = (ms: number) => new Date(NOW.getTime() - ms).toISOString();
const ahead = (ms: number) => new Date(NOW.getTime() + ms).toISOString();
const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

describe("invite text", () => {
  it("says when the invite was sent", () => {
    expect(sentText(ago(MINUTE), NOW)).toBe("just now");
    expect(sentText(ago(12 * MINUTE), NOW)).toBe("12 minutes ago");
    expect(sentText(ago(HOUR), NOW)).toBe("1 hour ago");
    expect(sentText(ago(30 * HOUR), NOW)).toBe("yesterday");
    expect(sentText(ago(5 * DAY + HOUR), NOW)).toBe("5 days ago");
  });

  it("counts whole days left, and flags the last two", () => {
    expect(expiryText(ahead(7 * DAY - MINUTE), NOW)).toBe("Expires in 7 days");
    expect(expiryText(ahead(DAY), NOW)).toBe("Expires in 1 day");
    expect(expiryText(ahead(DAY + HOUR), NOW)).toBe("Expires in 2 days");
    expect(expiryText(ahead(5 * HOUR), NOW)).toBe("Expires in under a day");
    expect(expiresSoon(ahead(2 * DAY), NOW)).toBe(true);
    expect(expiresSoon(ahead(2 * DAY + HOUR), NOW)).toBe(false);
  });

  it("builds the message to send with the code and where to enter it", () => {
    const message = shareMessage(
      { email: "bea@acme.com", code: "AB23-CD45", expires_at: "2026-10-06T12:00:00Z" },
      "Acme Talent",
      "https://fasthyr.com",
      "UTC",
    );
    expect(message).toContain("join Acme Talent");
    expect(message).toContain("https://fasthyr.com/workspaces");
    expect(message).toContain("bea@acme.com");
    expect(message).toContain("AB23-CD45");
  });

  it("checks email shape like the API", () => {
    expect(isEmail(" bea@acme.com ")).toBe(true);
    expect(isEmail("bea@acme")).toBe(false);
    expect(isEmail("bea acme@x.com")).toBe(false);
  });
});

describe("invite errors", () => {
  it("puts member and email errors on the email field", () => {
    expect(inviteFormError(new ApiError(409, "already_a_member", "x"))).toEqual({
      field: "email",
      key: "members.invites.inviteDialog.alreadyMember",
    });
    expect(inviteFormError(new ApiError(422, "validation_failed", "x")).field).toBe("email");
    expect(inviteFormError(new ApiError(422, "unknown_department", "x")).field).toBeNull();
    expect(inviteFormError(new Error("offline")).key).toBe("members.invites.errors.failed");
  });

  it("explains a resend or revoke on an invite that is gone", () => {
    expect(inviteActionErrorKey(new ApiError(404, "not_found", "x"))).toBe(
      "members.invites.errors.gone",
    );
    expect(inviteActionErrorKey(new Error("offline"))).toBe("members.invites.errors.failed");
  });
});

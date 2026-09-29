import {
  AuthApiError,
  AuthRetryableFetchError,
  AuthSessionMissingError,
} from "@supabase/supabase-js";
import { describe, expect, it, vi } from "vitest";

import { isValidEmail, requestPasswordReset, saveNewPassword } from "@/lib/auth/recovery";

function resetAuth(result: { error: Error | null } | Error) {
  return {
    resetPasswordForEmail:
      result instanceof Error
        ? vi.fn().mockRejectedValue(result)
        : vi.fn().mockResolvedValue({ data: {}, ...result }),
  };
}

describe("requestPasswordReset", () => {
  it("reads every answer from Supabase as sent, so it never reveals an account (FR-AUTH-02)", async () => {
    const answers = [
      null,
      new AuthApiError("wait", 429, "over_email_send_rate_limit"),
      new AuthApiError("mail failed", 500, "unexpected_failure"),
    ];
    for (const error of answers) {
      expect(await requestPasswordReset(resetAuth({ error }), " ta@example.com ")).toBe("sent");
    }
  });

  it("sends the trimmed email", async () => {
    const auth = resetAuth({ error: null });
    await requestPasswordReset(auth, " ta@example.com ");
    expect(auth.resetPasswordForEmail).toHaveBeenCalledWith("ta@example.com");
  });

  it("fails only when Supabase can't be reached", async () => {
    const offline = new AuthRetryableFetchError("Failed to fetch", 0);
    expect(await requestPasswordReset(resetAuth({ error: offline }), "ta@example.com")).toBe(
      "failed",
    );
    expect(await requestPasswordReset(resetAuth(new TypeError("fetch")), "ta@example.com")).toBe(
      "failed",
    );
  });
});

describe("saveNewPassword", () => {
  const save = (error: Error | null) =>
    saveNewPassword({ updateUser: vi.fn().mockResolvedValue({ data: {}, error }) }, "new-pass-1");

  it("maps Supabase's answers to what the page shows", async () => {
    expect(await save(null)).toBe("saved");
    expect(await save(new AuthSessionMissingError())).toBe("expired");
    expect(await save(new AuthApiError("gone", 403, "session_not_found"))).toBe("expired");
    expect(await save(new AuthApiError("same", 422, "same_password"))).toBe("same-password");
    expect(await save(new AuthApiError("weak", 422, "weak_password"))).toBe("weak-password");
    expect(await save(new AuthApiError("boom", 500, "unexpected_failure"))).toBe("failed");
  });
});

describe("isValidEmail", () => {
  it("accepts a normal address and rejects obvious typos", () => {
    expect(isValidEmail(" ta@company.com ")).toBe(true);
    expect(isValidEmail("ta@company")).toBe(false);
    expect(isValidEmail("ta company@x.com")).toBe(false);
    expect(isValidEmail("")).toBe(false);
  });
});

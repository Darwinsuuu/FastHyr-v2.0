import { AuthApiError, type User } from "@supabase/supabase-js";
import { describe, expect, it, vi } from "vitest";

import { continueWithPassword } from "@/lib/auth/password";

const details = {
  email: "ta@example.com",
  password: "correct-horse",
  emailRedirectTo: "http://fasthyr.localhost:3000/auth/callback",
};

function authError(code: string, status = 400) {
  return new AuthApiError(code, status, code);
}

function fakeAuth({
  signInError = null,
  signUpError = null,
  signUpUser = null,
}: {
  signInError?: AuthApiError | null;
  signUpError?: AuthApiError | null;
  signUpUser?: Partial<User> | null;
}) {
  return {
    signInWithPassword: vi.fn().mockResolvedValue({ data: {}, error: signInError }),
    signUp: vi
      .fn()
      .mockResolvedValue({ data: { user: signUpUser, session: null }, error: signUpError }),
  };
}

describe("continueWithPassword", () => {
  it("signs in an existing account without trying to create one", async () => {
    const auth = fakeAuth({});
    expect(await continueWithPassword(auth as never, details)).toBe("signed-in");
    expect(auth.signUp).not.toHaveBeenCalled();
  });

  it("rejects short passwords before calling Supabase", async () => {
    const auth = fakeAuth({});
    expect(await continueWithPassword(auth as never, { ...details, password: "short" })).toBe(
      "too-short",
    );
    expect(auth.signInWithPassword).not.toHaveBeenCalled();
  });

  it("creates the account when the details match none (New here?)", async () => {
    const auth = fakeAuth({
      signInError: authError("invalid_credentials"),
      signUpUser: { identities: [{} as never] },
    });
    expect(await continueWithPassword(auth as never, details)).toBe("check-email");
    expect(auth.signUp).toHaveBeenCalledWith({
      email: details.email,
      password: details.password,
      options: { emailRedirectTo: details.emailRedirectTo },
    });
  });

  it("treats an existing email as a wrong password, however Supabase reports it", async () => {
    const obfuscated = fakeAuth({
      signInError: authError("invalid_credentials"),
      signUpUser: { identities: [] },
    });
    expect(await continueWithPassword(obfuscated as never, details)).toBe("wrong-password");
    const refused = fakeAuth({
      signInError: authError("invalid_credentials"),
      signUpError: authError("user_already_exists", 422),
    });
    expect(await continueWithPassword(refused as never, details)).toBe("wrong-password");
  });

  it("asks unverified accounts to check their email", async () => {
    const auth = fakeAuth({ signInError: authError("email_not_confirmed") });
    expect(await continueWithPassword(auth as never, details)).toBe("check-email");
    expect(auth.signUp).not.toHaveBeenCalled();
  });
});

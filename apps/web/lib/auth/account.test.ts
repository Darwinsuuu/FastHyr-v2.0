import { describe, expect, it } from "vitest";

import { type AuthUserLike, accountDetails, signInMethods } from "./account";

const base: AuthUserLike = {
  id: "8f3c2a91-4d7e-4b1a-9c55-2e6f0b7d41a3",
  email: "bea@acme.test",
  email_confirmed_at: "2026-01-12T02:14:00Z",
  created_at: "2026-01-12T02:14:00Z",
  last_sign_in_at: "2026-09-26T00:31:00Z",
};

describe("sign-in methods", () => {
  it("names Azure as Microsoft and lists providers in a fixed order without duplicates", () => {
    const user = {
      ...base,
      identities: [{ provider: "email" }, { provider: "azure" }, { provider: "google" }],
      app_metadata: { provider: "email", providers: ["email", "azure", "google"] },
    };
    expect(signInMethods(user)).toEqual(["google", "microsoft", "email"]);
  });

  it("falls back to app metadata when identities are missing", () => {
    expect(signInMethods({ ...base, app_metadata: { provider: "google" } })).toEqual(["google"]);
  });

  it("ignores providers FastHyr doesn't offer", () => {
    expect(signInMethods({ ...base, identities: [{ provider: "github" }] })).toEqual([]);
  });
});

describe("account details", () => {
  it("takes the name and photo from the identity provider", () => {
    const account = accountDetails({
      ...base,
      identities: [{ provider: "google" }],
      user_metadata: { name: "Bea Garcia", picture: "https://example.test/bea.png" },
    });
    expect(account.name).toBe("Bea Garcia");
    expect(account.avatarUrl).toBe("https://example.test/bea.png");
    expect(account.profileSource).toBe("google");
    expect(account.emailVerified).toBe(true);
  });

  it("uses the email as the name for email + password accounts", () => {
    const account = accountDetails({
      ...base,
      email_confirmed_at: null,
      identities: [{ provider: "email" }],
    });
    expect(account.name).toBe("bea@acme.test");
    expect(account.avatarUrl).toBeNull();
    expect(account.profileSource).toBeNull();
    expect(account.emailVerified).toBe(false);
  });
});

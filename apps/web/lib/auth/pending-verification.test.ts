import { describe, expect, it } from "vitest";

import {
  cooldownLeft,
  forgetPendingVerification,
  parsePendingVerification,
  readPendingVerificationRaw,
  rememberPendingVerification,
} from "@/lib/auth/pending-verification";

function memoryStorage() {
  const items = new Map<string, string>();
  return {
    getItem: (key: string) => items.get(key) ?? null,
    setItem: (key: string, value: string) => void items.set(key, value),
    removeItem: (key: string) => void items.delete(key),
  };
}

describe("pending verification", () => {
  it("round-trips the email and send time, and forgets them", () => {
    const storage = memoryStorage();
    rememberPendingVerification(storage, { email: "ta@example.com", sentAt: 1000 });
    expect(parsePendingVerification(readPendingVerificationRaw(storage))).toEqual({
      email: "ta@example.com",
      sentAt: 1000,
    });
    forgetPendingVerification(storage);
    expect(parsePendingVerification(readPendingVerificationRaw(storage))).toBeNull();
  });

  it("ignores anything it didn't write", () => {
    expect(parsePendingVerification("not json")).toBeNull();
    expect(parsePendingVerification(JSON.stringify({ email: 3 }))).toBeNull();
  });
});

describe("cooldownLeft", () => {
  it("counts down 60 s from the last send and never goes outside 0–60", () => {
    expect(cooldownLeft(0, 0)).toBe(60);
    expect(cooldownLeft(0, 59_500)).toBe(1);
    expect(cooldownLeft(0, 60_000)).toBe(0);
    expect(cooldownLeft(0, 600_000)).toBe(0);
    expect(cooldownLeft(5_000, 0)).toBe(60);
  });
});

import { describe, expect, it } from "vitest";

import { applySource, parseJobDescription, parseSource, rememberSource } from "@/lib/apply";

class MemoryStorage {
  private items = new Map<string, string>();
  getItem(key: string) {
    return this.items.get(key) ?? null;
  }
  setItem(key: string, value: string) {
    this.items.set(key, value);
  }
}

describe("parseSource", () => {
  it("keeps known tags in any case", () => {
    expect(parseSource("linkedin")).toBe("linkedin");
    expect(parseSource(" JobStreet ")).toBe("jobstreet");
    expect(parseSource(["indeed", "other"])).toBe("indeed");
  });

  it("falls back to direct for missing or unknown values", () => {
    expect(parseSource(undefined)).toBe("direct");
    expect(parseSource("")).toBe("direct");
    expect(parseSource("twitter")).toBe("direct");
    expect(parseSource("direct")).toBe("direct");
  });
});

describe("source tag storage", () => {
  it("keeps the arrival tag per pipeline and never overwrites it with direct", () => {
    const storage = new MemoryStorage() as unknown as Storage;
    rememberSource(storage, "acme", "backend", "linkedin");
    rememberSource(storage, "acme", "backend", "direct");
    expect(applySource(storage, "acme", "backend")).toBe("linkedin");
    expect(applySource(storage, "acme", "designer")).toBe("direct");
    expect(applySource(undefined, "acme", "backend")).toBe("direct");
  });
});

describe("parseJobDescription", () => {
  it("splits paragraphs, headings and lists", () => {
    const text = [
      "You'll join the platform team.",
      "It runs our core services.",
      "",
      "What you'll do",
      "- Build services",
      "* Run them",
      "",
      "• Review code",
      "",
      "Requirements:",
      "1. Go or Java",
      "2) PostgreSQL",
      "",
      "About the team",
      "A small group that writes things down.",
    ].join("\r\n");
    expect(parseJobDescription(text)).toEqual([
      { kind: "paragraph", text: "You'll join the platform team. It runs our core services." },
      { kind: "heading", text: "What you'll do" },
      { kind: "list", items: ["Build services", "Run them", "Review code"] },
      { kind: "heading", text: "Requirements" },
      { kind: "list", items: ["Go or Java", "PostgreSQL"] },
      { kind: "heading", text: "About the team" },
      { kind: "paragraph", text: "A small group that writes things down." },
    ]);
  });

  it("keeps sentences and long lines as paragraphs", () => {
    expect(parseJobDescription("We hire kindly.\nAnd fast.")).toEqual([
      { kind: "paragraph", text: "We hire kindly. And fast." },
    ]);
    expect(parseJobDescription("A single short line")).toEqual([
      { kind: "paragraph", text: "A single short line" },
    ]);
  });
});

import { describe, expect, it } from "vitest";

import { initials, pairIndex } from "@/components/ui/avatar";
import { checkFile } from "@/components/ui/file-drop";
import { formatBytes } from "@/lib/format";

describe("initials", () => {
  it("takes the first letters of the first and last words", () => {
    expect(initials("Maria Santos")).toBe("MS");
    expect(initials("Kai Tanaka Cruz")).toBe("KC");
    expect(initials("  ana ")).toBe("A");
    expect(initials("")).toBe("?");
  });

  it("keeps a person's colour stable", () => {
    expect(pairIndex("user-1")).toBe(pairIndex("user-1"));
  });
});

describe("checkFile", () => {
  const pdf = (size: number) =>
    new File([new Uint8Array(size)], "cv.pdf", { type: "application/pdf" });

  it("accepts a file of an allowed type within the size", () => {
    expect(checkFile(pdf(1000), ["application/pdf"], 2000)).toBeNull();
  });

  it("rejects the wrong type and oversized files", () => {
    const image = new File(["x"], "cv.png", { type: "image/png" });
    expect(checkFile(image, ["application/pdf"], 2000)).toMatch(/isn't supported/);
    expect(checkFile(pdf(3000), ["application/pdf"], 2000)).toMatch(/larger than/);
  });
});

describe("formatBytes", () => {
  it("uses binary units", () => {
    expect(formatBytes(500, "en")).toBe("500 bytes");
    expect(formatBytes(10 * 1024 * 1024, "en")).toBe("10 MB");
    expect(formatBytes(1536, "en")).toBe("1.5 KB");
  });
});

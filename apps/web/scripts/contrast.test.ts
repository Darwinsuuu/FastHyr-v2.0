import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

// @ts-expect-error -- plain ESM script without type declarations
import { checkContrast, contrast } from "./check-contrast.mjs";

describe("contrast check", () => {
  it("computes WCAG ratios", () => {
    expect(contrast("#000000", "#FFFFFF")).toBeCloseTo(21, 5);
    expect(contrast("#777777", "#FFFFFF")).toBeCloseTo(4.48, 2);
  });

  it("passes for every pair the UI kit uses, in both themes", () => {
    const tokens = JSON.parse(
      readFileSync(new URL("../../../docs/design/tokens.json", import.meta.url), "utf8"),
    );
    expect(checkContrast(tokens)).toEqual([]);
  });
});

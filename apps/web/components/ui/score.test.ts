import { describe, expect, it } from "vitest";

import { splitHighlight } from "@/components/ui/insight-card";
import { weightedTotal } from "@/components/ui/weighted-calc";

describe("weightedTotal", () => {
  it("multiplies each score by its weight, adds them up and rounds", () => {
    const result = weightedTotal([
      { label: "Technical fit", score: 94, weight: 50 },
      { label: "Communication", score: 88, weight: 30 },
      { label: "Culture alignment", score: 86, weight: 20 },
    ]);
    expect(result.points).toEqual([47, 26.4, 17.2]);
    expect(result.exact).toBe(90.6);
    expect(result.rounded).toBe(91);
  });
});

describe("splitHighlight", () => {
  it("marks the first exact occurrence of the phrase", () => {
    expect(splitHighlight("Led payments migration in 2024", "payments migration")).toEqual([
      "Led ",
      "payments migration",
      " in 2024",
    ]);
  });

  it("marks nothing when the phrase isn't in the excerpt", () => {
    expect(splitHighlight("Led a migration", "payments")).toBeNull();
    expect(splitHighlight("Led a migration")).toBeNull();
  });
});

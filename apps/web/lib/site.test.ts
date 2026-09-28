import { describe, expect, it } from "vitest";

import { siteName, tagline } from "./site";

// Placeholder so `make test` has a web test to run; real tests arrive with features.
describe("site", () => {
  it("exposes the product name and tagline", () => {
    expect(siteName).toBe("FastHyr");
    expect(tagline).toBe("Every applicant, heard.");
  });
});

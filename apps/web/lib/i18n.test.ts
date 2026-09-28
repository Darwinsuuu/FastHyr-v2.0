import { describe, expect, it } from "vitest";

import { plural, t } from "./i18n";

describe("messages", () => {
  it("fills placeholders", () => {
    expect(t("app.signedInAs", { name: "Ada" })).toBe("Signed in as Ada");
  });

  it("picks the plural form by count", () => {
    expect(plural("app.memberCount", 1)).toBe("1 member");
    expect(plural("app.memberCount", 3)).toBe("3 members");
  });
});

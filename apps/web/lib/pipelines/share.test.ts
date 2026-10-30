import { describe, expect, it } from "vitest";

import { PENDING_ACTIONS } from "@/lib/pipelines/list";
import { hasApplyLink, shareLinksBySource } from "@/lib/pipelines/share";

describe("share apply link", () => {
  it("offers the link for every pipeline with an apply page, scheduled ones included", () => {
    for (const status of ["scheduled", "live", "paused", "paused_no_credits", "closed"] as const) {
      expect(hasApplyLink(status)).toBe(true);
    }
    expect(hasApplyLink("draft")).toBe(false);
    expect(hasApplyLink("cancelled")).toBe(false);
  });

  it("keys the API's links by source", () => {
    const links = shareLinksBySource([
      { source: "linkedin", url: "https://fasthyr.com/apply/acme/qa?source=linkedin" },
      { source: "other", url: "https://fasthyr.com/apply/acme/qa?source=other" },
    ]);
    expect(links.linkedin).toBe("https://fasthyr.com/apply/acme/qa?source=linkedin");
    expect(links.other).toBe("https://fasthyr.com/apply/acme/qa?source=other");
  });

  it("lets Copy apply link be picked from the menus", () => {
    expect(PENDING_ACTIONS).not.toContain("copyLink");
  });
});

import { describe, expect, it } from "vitest";

import { cardState, contactHref, type ReviewLink } from "@/lib/review-request";

const link = (changes: Partial<ReviewLink> = {}): ReviewLink => ({
  state: "open",
  company: { name: "Acme", logo_url: null, website: "https://acme.test", careers_url: null },
  job_title: "Backend Engineer",
  ...changes,
});

describe("review request page", () => {
  it("thanks the candidate right after they ask, and says so on a later visit", () => {
    expect(cardState(link({ state: "requested" }), true)).toBe("sent");
    expect(cardState(link({ state: "requested" }), false)).toBe("requested");
    expect(cardState(link({ state: "expired" }), true)).toBe("expired");
    expect(cardState(link(), false)).toBe("open");
  });

  it("points closed links at the careers page, else the website", () => {
    expect(contactHref(link().company)).toBe("https://acme.test");
    expect(contactHref({ ...link().company, careers_url: "https://acme.test/careers" })).toBe(
      "https://acme.test/careers",
    );
    expect(contactHref({ ...link().company, website: null })).toBeNull();
  });
});

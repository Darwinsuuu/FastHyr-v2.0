import { describe, expect, it } from "vitest";

import { FILTERED, scrubBreadcrumb, scrubEvent, scrubUrl } from "./scrub";
import { tagApiError } from "./sentry";

// Personal data planted in the fixture; none of it may reach Sentry.
const PERSONAL = ["ada@example.com", "Ada Lovelace", "s3cret-pass", "eyJhbGciOi", "inv_tok_123"];
const JWT = "eyJhbGciOiJFUzI1NiJ9.eyJzdWIiOiIxIn0.c2lnbmF0dXJl";

describe("Sentry scrubbing", () => {
  it("removes personal data from every part of an event", () => {
    const event = scrubEvent({
      message: "invite for ada@example.com failed",
      transaction: "/join/inv_tok_123",
      request: {
        method: "GET",
        url: "https://fasthyr.com/join/inv_tok_123?email=ada@example.com#x",
        headers: { Authorization: `Bearer ${JWT}`, Cookie: `sb=${JWT}`, "User-Agent": "UA" },
        cookies: { sb: JWT },
        query_string: "email=ada@example.com",
      },
      user: { id: "u1", email: "ada@example.com", ip_address: "1.2.3.4" },
      extra: { candidateEmail: "ada@example.com", full_name: "Ada Lovelace", count: 2 },
      contexts: { form: { password: "s3cret-pass", name: "Ada Lovelace" } },
      exception: {
        values: [
          {
            type: "Error",
            value: `bad token ${JWT}`,
            stacktrace: { frames: [{ function: "f", vars: { who: "Ada Lovelace" } }] },
          },
        ],
      },
      breadcrumbs: [
        { category: "navigation", data: { from: "/join/inv_tok_123", to: "/login?next=/a" } },
        { category: "console", message: "signed in as ada@example.com" },
      ],
      server_name: "vercel-1",
    });

    const text = JSON.stringify(event);
    for (const planted of PERSONAL) expect(text).not.toContain(planted);
    expect(event.request?.url).toBe(`https://fasthyr.com/join/${FILTERED}`);
    expect(event.request?.headers).toEqual({ "User-Agent": "UA" });
    expect(event.user).toEqual({ id: "u1" });
    expect(event.extra?.count).toBe(2);
    expect(event.breadcrumbs?.[0]?.data?.to).toBe("/login");
    expect(event.server_name).toBeUndefined();
  });

  it("strips query strings and fragments from URLs", () => {
    expect(scrubUrl("https://x.test/auth/confirm?token_hash=abc#t")).toBe(
      "https://x.test/auth/confirm",
    );
    expect(scrubBreadcrumb({ data: { url: "/v1/me?x=1" } }).data?.url).toBe("/v1/me");
  });

  it("tags API errors with the API's request ID", () => {
    const error = Object.assign(new Error("Not found"), {
      name: "ApiError",
      status: 404,
      code: "not_found",
      requestId: "req-12345678",
    });
    const event = tagApiError({ type: undefined }, { originalException: error });
    expect(event.tags).toEqual({
      request_id: "req-12345678",
      api_status: "404",
      api_code: "not_found",
    });
  });
});

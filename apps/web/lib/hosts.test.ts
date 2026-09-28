import { describe, expect, it } from "vitest";

import { hostOf, internalPath, loginRedirect, safeNextPath } from "./hosts";

const APP_URL = "http://app.fasthyr.localhost:3000";

describe("host routing", () => {
  it("sends the app host to the TA folder and everything else to the site", () => {
    expect(hostOf("app.fasthyr.localhost:3000", APP_URL)).toBe("app");
    expect(hostOf("APP.FASTHYR.LOCALHOST", APP_URL)).toBe("app");
    expect(hostOf("fasthyr.localhost:3000", APP_URL)).toBe("site");
    expect(hostOf("app.evil.example", APP_URL)).toBe("site");
    expect(hostOf(null, APP_URL)).toBe("site");
    expect(hostOf("app.fasthyr.com", "https://app.fasthyr.com")).toBe("app");
  });

  it("rewrites paths into the host's folder", () => {
    expect(internalPath("app", "/")).toBe("/ta");
    expect(internalPath("app", "/pipelines")).toBe("/ta/pipelines");
    expect(internalPath("site", "/login")).toBe("/site/login");
  });
});

describe("signed-out redirect", () => {
  it("goes to the site's login page and keeps where the visitor was going", () => {
    const url = loginRedirect("https://fasthyr.com", "/pipelines", "?tab=candidates");
    expect(url.toString()).toBe("https://fasthyr.com/login?next=%2Fpipelines%3Ftab%3Dcandidates");
    expect(loginRedirect("https://fasthyr.com", "/", "").toString()).toBe(
      "https://fasthyr.com/login",
    );
  });

  it("only returns to paths on our own host", () => {
    expect(safeNextPath("/pipelines?tab=ava")).toBe("/pipelines?tab=ava");
    expect(safeNextPath("https://evil.example")).toBe("/");
    expect(safeNextPath("//evil.example")).toBe("/");
    expect(safeNextPath("/\\evil.example")).toBe("/");
    expect(safeNextPath(null)).toBe("/");
  });
});

import { describe, expect, it } from "vitest";

import { chooseDestination } from "@/lib/auth/destination";

const A = "11111111-1111-4111-8111-111111111111";
const B = "22222222-2222-4222-8222-222222222222";
const C = "33333333-3333-4333-8333-333333333333";

describe("chooseDestination", () => {
  it("sends users with no workspace to Choose workspace, whatever next says", () => {
    expect(
      chooseDestination({
        next: "/pipelines",
        lastWorkspaceId: null,
        cookieWorkspaceId: null,
        workspaceIds: [],
      }),
    ).toEqual({ host: "site", path: "/workspaces", workspaceId: null });
  });

  it("opens the last active workspace from the profile first", () => {
    expect(
      chooseDestination({
        next: null,
        lastWorkspaceId: B,
        cookieWorkspaceId: A,
        workspaceIds: [A, B],
      }),
    ).toEqual({ host: "app", path: "/", workspaceId: B });
  });

  it("falls back to this device's workspace, then the first one", () => {
    const base = { next: null, lastWorkspaceId: C, workspaceIds: [A, B] };
    expect(chooseDestination({ ...base, cookieWorkspaceId: B }).workspaceId).toBe(B);
    // C is a workspace the user has left, so it is skipped.
    expect(chooseDestination({ ...base, cookieWorkspaceId: C }).workspaceId).toBe(A);
  });

  it("honours a same-host next path and ignores anything else", () => {
    const base = { lastWorkspaceId: null, cookieWorkspaceId: null, workspaceIds: [A] };
    expect(chooseDestination({ ...base, next: "/pipelines?tab=live" }).path).toBe(
      "/pipelines?tab=live",
    );
    expect(chooseDestination({ ...base, next: "//evil.example" }).path).toBe("/");
    expect(chooseDestination({ ...base, next: "https://evil.example" }).path).toBe("/");
  });
});

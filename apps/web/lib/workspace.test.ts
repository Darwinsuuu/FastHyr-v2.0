import { describe, expect, it } from "vitest";

import { readWorkspaceId } from "./workspace";

describe("active workspace cookie", () => {
  it("reads a workspace UUID and ignores anything else", () => {
    const id = "0192f5a0-0000-7000-8000-000000000001";
    expect(readWorkspaceId(`sb-auth=x; fh_ws=${id}; other=1`)).toBe(id);
    expect(readWorkspaceId("fh_ws=not-a-uuid")).toBeNull();
    expect(readWorkspaceId("")).toBeNull();
  });
});

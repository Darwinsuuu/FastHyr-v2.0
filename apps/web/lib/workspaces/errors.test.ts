import { ApiError } from "@fasthyr/api-client";
import { describe, expect, it } from "vitest";

import { createErrorKey, joinErrorKey, workspaceNameError } from "@/lib/workspaces/errors";

const problem = (status: number, code: string) => new ApiError(status, code, "title");

describe("joinErrorKey", () => {
  it("explains each invite problem the API reports", () => {
    expect(joinErrorKey(problem(404, "invite_not_found"))).toBe(
      "workspaces.joinError.invite_not_found",
    );
    expect(joinErrorKey(problem(403, "invite_wrong_email"))).toBe(
      "workspaces.joinError.invite_wrong_email",
    );
    expect(joinErrorKey(problem(410, "invite_expired"))).toBe(
      "workspaces.joinError.invite_expired",
    );
    expect(joinErrorKey(problem(410, "invite_invalid"))).toBe(
      "workspaces.joinError.invite_invalid",
    );
    expect(joinErrorKey(problem(403, "email_not_verified"))).toBe("workspaces.emailNotVerified");
  });

  it("treats anything else, including no answer, as a failure to try again", () => {
    expect(joinErrorKey(problem(500, "internal_error"))).toBe("workspaces.joinError.failed");
    expect(joinErrorKey(new TypeError("Failed to fetch"))).toBe("workspaces.joinError.failed");
  });
});

describe("createErrorKey", () => {
  it("asks unverified users to verify, and anything else to try again", () => {
    expect(createErrorKey(problem(403, "email_not_verified"))).toBe("workspaces.emailNotVerified");
    expect(createErrorKey(new TypeError("Failed to fetch"))).toBe("workspaces.createFailed");
  });
});

describe("workspaceNameError", () => {
  it("matches the API's 1 to 120 characters after trimming", () => {
    expect(workspaceNameError("   ")).toBe("workspaces.nameRequired");
    expect(workspaceNameError(` ${"x".repeat(120)} `)).toBeNull();
    expect(workspaceNameError("x".repeat(121))).toBe("workspaces.nameTooLong");
  });
});

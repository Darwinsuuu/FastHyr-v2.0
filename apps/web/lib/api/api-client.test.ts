import { ApiError, createApiClient, unwrap } from "@fasthyr/api-client";
import { describe, expect, it } from "vitest";

function fakeFetch(response: Response, seen: Request[]) {
  return async (input: RequestInfo | URL, init?: RequestInit) => {
    seen.push(new Request(input, init));
    return response;
  };
}

describe("API client", () => {
  it("sends the access token and active workspace", async () => {
    const seen: Request[] = [];
    const api = createApiClient({
      baseUrl: "http://api.test",
      getAccessToken: async () => "token-123",
      getWorkspaceId: () => "0192f5a0-0000-7000-8000-000000000001",
      fetch: fakeFetch(Response.json([]), seen),
    });

    unwrap(await api.GET("/v1/me/workspaces"));

    expect(seen[0]?.headers.get("Authorization")).toBe("Bearer token-123");
    expect(seen[0]?.headers.get("X-Workspace-Id")).toBe("0192f5a0-0000-7000-8000-000000000001");
  });

  it("sends nothing extra when signed out", async () => {
    const seen: Request[] = [];
    const api = createApiClient({
      baseUrl: "http://api.test",
      getAccessToken: () => null,
      fetch: fakeFetch(Response.json({ status: "ok" }), seen),
    });

    await api.GET("/health");

    expect(seen[0]?.headers.has("Authorization")).toBe(false);
    expect(seen[0]?.headers.has("X-Workspace-Id")).toBe(false);
  });

  it("turns problem+json into an ApiError with its code", async () => {
    const problem = new Response(
      JSON.stringify({
        type: "https://fasthyr.com/errors/not_a_member",
        title: "You are not a member of this workspace",
        status: 403,
        code: "not_a_member",
        request_id: "req-1",
      }),
      { status: 403, headers: { "content-type": "application/problem+json" } },
    );
    const api = createApiClient({ baseUrl: "http://api.test", fetch: fakeFetch(problem, []) });

    const error = await api
      .GET("/v1/me")
      .then(unwrap)
      .catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 403, code: "not_a_member", requestId: "req-1" });
  });
});

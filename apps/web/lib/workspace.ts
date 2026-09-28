// The active workspace lives in the `fh_ws` cookie (FRONTEND.md §1) and goes to the API as
// `X-Workspace-Id`. It holds only the workspace UUID. Switching replaces the cookie and the
// caller resets the query cache (see useSwitchWorkspace in lib/api/provider.tsx).

import { env } from "@/lib/env";

export const WORKSPACE_COOKIE = "fh_ws";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function readWorkspaceId(cookieHeader: string): string | null {
  for (const part of cookieHeader.split(";")) {
    const [name, ...rest] = part.trim().split("=");
    if (name === WORKSPACE_COOKIE) {
      const value = decodeURIComponent(rest.join("="));
      return UUID.test(value) ? value : null;
    }
  }
  return null;
}

export function workspaceCookie(workspaceId: string | null): string {
  const attributes = [
    "Path=/",
    "SameSite=Lax",
    ...(env.cookieDomain ? [`Domain=${env.cookieDomain}`] : []),
    ...(env.siteUrl.startsWith("https://") ? ["Secure"] : []),
  ];
  return workspaceId
    ? [
        `${WORKSPACE_COOKIE}=${encodeURIComponent(workspaceId)}`,
        "Max-Age=31536000",
        ...attributes,
      ].join("; ")
    : [`${WORKSPACE_COOKIE}=`, "Max-Age=0", ...attributes].join("; ");
}

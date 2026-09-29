"use client";

import { api } from "@/lib/api/client";
import { workspaceCookie } from "@/lib/workspace";

/**
 * Makes a workspace the active one: the `fh_ws` cookie for this device, and
 * `profiles.last_workspace_id` so the next sign-in on any device lands there (FR-AUTH-04).
 * Callers that stay on the page also clear the query cache (useSwitchWorkspace).
 */
export async function activateWorkspace(workspaceId: string): Promise<void> {
  document.cookie = workspaceCookie(workspaceId);
  // Best effort: the cookie already makes it active on this device.
  await api
    .PUT("/v1/me/last-workspace", { body: { workspace_id: workspaceId } })
    .catch(() => undefined);
}

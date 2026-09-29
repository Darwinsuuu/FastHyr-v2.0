// Where a TA user goes after signing in (FR-AUTH-04). /auth/continue runs this for every
// sign-in method so the rule lives in one place.

import { safeNextPath } from "@/lib/hosts";

export type Destination =
  /** An app-host path, with the workspace to make active first. */
  | { host: "app"; path: string; workspaceId: string | null }
  /** Choose workspace (/workspaces on the site host): the user has no workspace yet. */
  | { host: "site"; path: "/workspaces"; workspaceId: null };

export interface DestinationInput {
  /** The `next` query parameter, if any. Only same-host paths are honoured. */
  next: string | null;
  /** `last_workspace_id` from /v1/me. */
  lastWorkspaceId: string | null | undefined;
  /** The `fh_ws` cookie: the workspace last used on this device. */
  cookieWorkspaceId: string | null;
  /** IDs of the user's active workspaces from /v1/me/workspaces, in API order. */
  workspaceIds: string[];
}

export function chooseDestination({
  next,
  lastWorkspaceId,
  cookieWorkspaceId,
  workspaceIds,
}: DestinationInput): Destination {
  if (workspaceIds.length === 0) {
    return { host: "site", path: "/workspaces", workspaceId: null };
  }
  const workspaceId =
    [lastWorkspaceId, cookieWorkspaceId].find(
      (id): id is string => !!id && workspaceIds.includes(id),
    ) ?? workspaceIds[0]!;
  return { host: "app", path: safeNextPath(next), workspaceId };
}

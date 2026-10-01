// Where a TA user goes after signing in (FR-AUTH-04). /auth/continue runs this for every
// sign-in method so the rule lives in one place.

import { safeNextPath } from "@/lib/hosts";

export type Destination =
  /** An app-host path, with the workspace to make active first. */
  | { host: "app"; path: string; workspaceId: string | null }
  /**
   * A site-host page: Choose workspace (/workspaces) when the user has no workspace yet, or the
   * invite they opened before signing in (/join/{code}).
   */
  | { host: "site"; path: string; workspaceId: null };

/** Join a workspace from an invite (S-04) lives on the site host. */
export function isJoinPath(next: string | null): next is string {
  return !!next && /^\/join\/[^/?#\\]+$/.test(next);
}

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
  // An invitee usually has no workspace yet; they still go back to the invite they opened.
  if (isJoinPath(next)) {
    return { host: "site", path: next, workspaceId: null };
  }
  if (workspaceIds.length === 0) {
    return { host: "site", path: "/workspaces", workspaceId: null };
  }
  const workspaceId =
    [lastWorkspaceId, cookieWorkspaceId].find(
      (id): id is string => !!id && workspaceIds.includes(id),
    ) ?? workspaceIds[0]!;
  return { host: "app", path: safeNextPath(next), workspaceId };
}

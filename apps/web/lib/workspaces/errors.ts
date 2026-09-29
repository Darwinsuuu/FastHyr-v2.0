// Copy for the Choose workspace page's API errors, by problem+json `code` (never by title).

import { ApiError } from "@fasthyr/api-client";

import type { MessageKey } from "@/lib/i18n";

const JOIN_ERRORS: Record<string, MessageKey> = {
  invite_not_found: "workspaces.joinError.invite_not_found",
  invite_wrong_email: "workspaces.joinError.invite_wrong_email",
  invite_expired: "workspaces.joinError.invite_expired",
  invite_invalid: "workspaces.joinError.invite_invalid",
  // A pasted link or code longer than any real one fails validation: it can't be an invite.
  validation_failed: "workspaces.joinError.invite_not_found",
  email_not_verified: "workspaces.emailNotVerified",
};

export function joinErrorKey(error: unknown): MessageKey {
  return (error instanceof ApiError && JOIN_ERRORS[error.code]) || "workspaces.joinError.failed";
}

export function createErrorKey(error: unknown): MessageKey {
  if (error instanceof ApiError && error.code === "email_not_verified") {
    return "workspaces.emailNotVerified";
  }
  return "workspaces.createFailed";
}

/** Same limits as the API (1 to 120 characters after trimming). */
export function workspaceNameError(name: string): MessageKey | null {
  const trimmed = name.trim();
  if (!trimmed) return "workspaces.nameRequired";
  if (trimmed.length > 120) return "workspaces.nameTooLong";
  return null;
}

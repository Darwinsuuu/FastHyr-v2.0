// Member invites logic (WS-004): "sent" and expiry text, the message to send, and error copy.

import { ApiError, type components } from "@fasthyr/api-client";

import { formatDate } from "@/lib/format";
import { type MessageKey, plural, t } from "@/lib/i18n";

export type Invite = components["schemas"]["Invite"];

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** An invite lasts 7 days from its latest send (FR-WS-03). */
export const INVITE_DAYS = 7;

// The API's check: something@domain.tld with no spaces.
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export function isEmail(value: string): boolean {
  return EMAIL.test(value.trim());
}

/** "just now", "12 minutes ago", "3 hours ago", "yesterday", "4 days ago". */
export function sentText(sentAt: string, now: Date): string {
  const elapsed = Math.max(0, now.getTime() - new Date(sentAt).getTime());
  if (elapsed < 5 * MINUTE) return t("members.invites.sent.now");
  if (elapsed < HOUR) return plural("members.invites.sent.minutes", Math.floor(elapsed / MINUTE));
  if (elapsed < DAY) return plural("members.invites.sent.hours", Math.floor(elapsed / HOUR));
  if (elapsed < 2 * DAY) return t("members.invites.sent.yesterday");
  return plural("members.invites.sent.days", Math.floor(elapsed / DAY));
}

/** "Expires in 7 days" … "Expires in under a day". */
export function expiryText(expiresAt: string, now: Date): string {
  const left = new Date(expiresAt).getTime() - now.getTime();
  if (left < DAY) return t("members.invites.expires.underADay");
  return plural("members.invites.expires.days", Math.ceil(left / DAY));
}

/** Two days or less left: the list shows the expiry in amber so it gets resent in time. */
export function expiresSoon(expiresAt: string, now: Date): boolean {
  return new Date(expiresAt).getTime() - now.getTime() <= 2 * DAY;
}

/** When a resent invite would expire: 7 days from now. */
export function nextExpiry(now: Date): Date {
  return new Date(now.getTime() + INVITE_DAYS * DAY);
}

/** The message the Admin sends until invite emails go out (FND-010). */
export function shareMessage(
  invite: Pick<Invite, "email" | "code" | "expires_at">,
  workspace: string,
  siteUrl: string,
  timeZone: string,
): string {
  return t("members.invites.shareDialog.text", {
    workspace,
    url: new URL("/workspaces", siteUrl).toString(),
    email: invite.email,
    code: invite.code,
    date: formatDate(invite.expires_at, timeZone),
  });
}

/** The message for a failed resend or revoke. */
export function inviteActionErrorKey(error: unknown): MessageKey {
  if (error instanceof ApiError && error.status === 404) return "members.invites.errors.gone";
  return "members.invites.errors.failed";
}

/** Where the invite form shows a failed send: on the email field, or as a toast. */
export function inviteFormError(
  error: unknown,
): { field: "email"; key: MessageKey } | { field: null; key: MessageKey } {
  if (error instanceof ApiError) {
    if (error.code === "already_a_member")
      return { field: "email", key: "members.invites.inviteDialog.alreadyMember" };
    if (error.code === "validation_failed")
      return { field: "email", key: "members.invites.inviteDialog.emailInvalid" };
    if (error.code === "unknown_department")
      return { field: null, key: "members.invites.errors.department" };
  }
  return { field: null, key: "members.invites.errors.failed" };
}

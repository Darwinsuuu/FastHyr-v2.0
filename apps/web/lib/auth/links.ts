// Where Supabase's auth emails send people (AUTH-002). The templates in supabase/templates link to
// /auth/confirm with a token hash, which works in any browser, unlike the PKCE code link.

import { env } from "@/lib/env";

export type EmailLinkType = "email" | "recovery";

/**
 * `emailRedirectTo` for sign-up and resend. The confirmation template appends
 * `&token_hash=…&type=email`, so this URL always carries a query string.
 */
export function verifyEmailRedirect(next: string | null): string {
  const url = new URL("/auth/confirm", env.siteUrl);
  url.searchParams.set("next", next ?? "");
  return url.toString();
}

export function isEmailLinkType(value: string | null): value is EmailLinkType {
  return value === "email" || value === "recovery";
}

/** Where /auth/confirm sends someone after checking the link's token. */
export function confirmDestination({
  type,
  verified,
  continueTo,
}: {
  type: string | null;
  verified: boolean;
  /** The /auth/continue path, with the link's `next`. */
  continueTo: string;
}): string {
  if (type === "recovery") {
    return verified ? "/reset-password" : "/reset-password?error=link-expired";
  }
  return verified ? continueTo : "/login?error=link-expired";
}

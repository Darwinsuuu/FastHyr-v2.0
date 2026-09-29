// "Forgot password" (FR-AUTH-02): ask Supabase to email a reset link. The answer never says
// whether an account exists, so the only outcome besides "sent" is a failure to reach Supabase.

import {
  type AuthError,
  isAuthApiError,
  isAuthSessionMissingError,
  type SupabaseClient,
} from "@supabase/supabase-js";

type Auth = Pick<SupabaseClient["auth"], "resetPasswordForEmail" | "updateUser">;

export type ResetRequestOutcome = "sent" | "failed";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function isValidEmail(email: string): boolean {
  return EMAIL_PATTERN.test(email.trim());
}

export async function requestPasswordReset(
  auth: Pick<Auth, "resetPasswordForEmail">,
  email: string,
): Promise<ResetRequestOutcome> {
  try {
    const { error } = await auth.resetPasswordForEmail(email.trim());
    // Supabase answers an unknown email with success, but refuses a second email to a real account
    // within a minute (429) or reports a mail failure for it. Showing either would tell anyone the
    // account exists, so every answer from Supabase reads as sent; only no answer is an error.
    return !error || isAuthApiError(error) ? "sent" : "failed";
  } catch {
    return "failed";
  }
}

export type NewPasswordOutcome =
  | "saved"
  /** No reset session any more: the link was never opened here, or the session ended. */
  | "expired"
  | "same-password"
  | "weak-password"
  | "rate-limited"
  | "failed";

function fromUpdateError(error: AuthError): NewPasswordOutcome {
  if (isAuthSessionMissingError(error)) return "expired";
  switch (error.code) {
    case "session_not_found":
    case "session_expired":
    case "refresh_token_not_found":
      return "expired";
    case "same_password":
      return "same-password";
    case "weak_password":
      return "weak-password";
    case "over_request_rate_limit":
      return "rate-limited";
    default:
      return "failed";
  }
}

/** Sets the password of the user the reset link signed in (S-05). */
export async function saveNewPassword(
  auth: Pick<Auth, "updateUser">,
  password: string,
): Promise<NewPasswordOutcome> {
  try {
    const { error } = await auth.updateUser({ password });
    return error ? fromUpdateError(error) : "saved";
  } catch {
    return "failed";
  }
}

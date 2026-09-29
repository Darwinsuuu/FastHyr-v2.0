// Email + password sign-in with "New here?" built in (FR-AUTH-01): one Continue button signs in
// an existing account or, when the details match no account, creates one. New accounts must
// verify their email before they can sign in (FR-AUTH-03).

import type { AuthError, SupabaseClient, User } from "@supabase/supabase-js";

export const MIN_PASSWORD_LENGTH = 8;

export type PasswordOutcome =
  | "signed-in"
  /** A verification email is on its way (new account) or still waiting to be opened. */
  | "check-email"
  /** The account exists and the password is wrong, or it signs in with Google or Microsoft. */
  | "wrong-password"
  | "too-short"
  | "weak-password"
  | "rate-limited"
  | "failed";

type Auth = Pick<SupabaseClient["auth"], "signInWithPassword" | "signUp">;

function isNewUser(user: User | null): boolean {
  // With email confirmation on, Supabase answers a sign-up for an existing email with a user that
  // has no identities, and sends nothing.
  return !!user && (user.identities?.length ?? 0) > 0;
}

function fromError(error: AuthError): PasswordOutcome {
  switch (error.code) {
    case "email_not_confirmed":
      return "check-email";
    case "invalid_credentials":
    case "user_already_exists":
    case "email_exists":
      return "wrong-password";
    case "weak_password":
      return "weak-password";
    case "over_email_send_rate_limit":
    case "over_request_rate_limit":
      return "rate-limited";
    default:
      return "failed";
  }
}

export async function continueWithPassword(
  auth: Auth,
  {
    email,
    password,
    emailRedirectTo,
  }: { email: string; password: string; emailRedirectTo: string },
): Promise<PasswordOutcome> {
  if (password.length < MIN_PASSWORD_LENGTH) {
    return "too-short";
  }
  const signIn = await auth.signInWithPassword({ email, password });
  if (!signIn.error) {
    return "signed-in";
  }
  if (signIn.error.code !== "invalid_credentials") {
    return fromError(signIn.error);
  }
  const signUp = await auth.signUp({ email, password, options: { emailRedirectTo } });
  if (signUp.error) {
    return fromError(signUp.error);
  }
  if (signUp.data.session) {
    // Only when email confirmation is off for the project.
    return "signed-in";
  }
  return isNewUser(signUp.data.user) ? "check-email" : "wrong-password";
}

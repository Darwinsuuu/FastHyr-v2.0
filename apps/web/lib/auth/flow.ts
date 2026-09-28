// Shared pieces of the sign-in flow (AUTH-001): the providers, and the /auth/continue step that
// every method passes through before landing in the app.

export type OAuthProvider = "google" | "azure";

export const OAUTH_PROVIDERS: readonly OAuthProvider[] = ["google", "azure"];

// Microsoft returns no email or name unless these scopes are asked for (FND-002 log).
export const OAUTH_SCOPES: Record<OAuthProvider, string | undefined> = {
  google: undefined,
  azure: "email profile",
};

export function isOAuthProvider(value: string | null | undefined): value is OAuthProvider {
  return OAUTH_PROVIDERS.includes(value as OAuthProvider);
}

/** The site-host path that picks the post-sign-in destination (app/site/auth/continue). */
export function continuePath(next: string | null): string {
  return next ? `/auth/continue?next=${encodeURIComponent(next)}` : "/auth/continue";
}

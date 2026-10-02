// Candidate sign-in on the apply page (APPLY-002): who is signed in, and the OAuth round trip
// that brings them back to the same page with the form open (ADR-014: Google or Microsoft only).

import type { OAuthProvider } from "@/lib/auth/flow";
import type { SourceTag } from "@/lib/apply";

export interface Candidate {
  id: string;
  name: string;
  email: string;
  provider: OAuthProvider;
}

/** The session claims this module reads (Supabase access token). */
export interface CandidateClaims {
  sub: string;
  email?: string;
  app_metadata?: { provider?: string; providers?: string[] };
  user_metadata?: { full_name?: string; name?: string };
}

/**
 * The signed-in candidate, or null. Only a Google or Microsoft session counts: candidates never
 * use email + password, so a TA user's password session sees the page signed out.
 */
export function candidateFromClaims(claims: CandidateClaims | null | undefined): Candidate | null {
  if (!claims?.sub || !claims.email) return null;
  const app = claims.app_metadata ?? {};
  const providers = [app.provider, ...(app.providers ?? [])];
  const provider = providers.find(
    (item): item is OAuthProvider => item === "google" || item === "azure",
  );
  if (!provider) return null;
  const meta = claims.user_metadata ?? {};
  return {
    id: claims.sub,
    name: meta.full_name || meta.name || claims.email,
    email: claims.email,
    provider,
  };
}

/** Why the modal opened: Apply now opens the form after sign-in, the header's Sign in doesn't. */
export type SignInIntent = "apply" | "browse";

/** Query parameters the round trip adds to the apply page; removed again once read. */
export const APPLY_PARAM = "apply";
export const SIGNIN_PARAM = "signin";

export type SignInProblem = "cancelled" | "failed";

/** Where the provider sends the candidate back to: this apply page, with the form to open. */
export function applyReturnPath(
  workspaceSlug: string,
  pipelineSlug: string,
  { intent, source }: { intent: SignInIntent; source: SourceTag },
): string {
  const params = new URLSearchParams();
  if (intent === "apply") params.set(APPLY_PARAM, "1");
  if (source !== "direct") params.set("source", source);
  const query = params.toString();
  const path = `/apply/${encodeURIComponent(workspaceSlug)}/${encodeURIComponent(pipelineSlug)}`;
  return query ? `${path}?${query}` : path;
}

/** An apply page on the site host, optionally with a query string. */
export function isApplyPath(next: string | null | undefined): next is string {
  return !!next && /^\/apply\/[^/?#\\]+\/[^/?#\\]+(?:\?[^#\\]*)?$/.test(next);
}

/** The apply page again after a cancelled or failed sign-in, so the modal can say what happened. */
export function applySignInProblemPath(next: string, problem: SignInProblem): string {
  const url = new URL(next, "http://apply.invalid");
  url.searchParams.set(SIGNIN_PARAM, problem);
  return `${url.pathname}${url.search}`;
}

export interface ReturnState {
  /** Open the application form (signed in, came back with the apply intent). */
  openForm: boolean;
  /** Reopen sign-in with this problem (the provider sent the candidate back without a session). */
  problem: SignInProblem | null;
  /** The intent to reopen sign-in with. */
  intent: SignInIntent;
  /** True when the address bar has round-trip parameters to remove. */
  clean: boolean;
}

/** What the page does with the round trip's parameters when it loads. */
export function readReturn(search: URLSearchParams, signedIn: boolean): ReturnState {
  const wantsForm = search.get(APPLY_PARAM) === "1";
  const signin = search.get(SIGNIN_PARAM);
  const problem = signin === "cancelled" || signin === "failed" ? signin : null;
  return {
    openForm: wantsForm && signedIn,
    problem: signedIn ? null : problem,
    intent: wantsForm ? "apply" : "browse",
    clean: search.has(APPLY_PARAM) || search.has(SIGNIN_PARAM),
  };
}

/** The address bar without the round trip's parameters (`source` stays). */
export function withoutReturnParams(pathname: string, search: URLSearchParams): string {
  const params = new URLSearchParams(search);
  params.delete(APPLY_PARAM);
  params.delete(SIGNIN_PARAM);
  const query = params.toString();
  return query ? `${pathname}?${query}` : pathname;
}

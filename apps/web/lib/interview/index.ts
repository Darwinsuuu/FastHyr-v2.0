// The interview link page (INTV-002, SCREEN_SPECS.md S-01): its states and the sign-in round trip
// that brings the candidate back to the same link (ADR-014: Google or Microsoft only). The device
// check's media helpers are in `./devices` (INTV-003).

import type { components } from "@fasthyr/api-client";

import { SIGNIN_PARAM, type SignInProblem } from "@/lib/apply/session";

export type InterviewLink = components["schemas"]["InterviewLink"];
export type InterviewLinkState = InterviewLink["state"];
export type InterviewCompany = InterviewLink["company"];

/** States from which the candidate goes through the device check (the API's OPEN_STATES). */
const OPEN_STATES: readonly InterviewLinkState[] = ["welcome", "resume", "technical_problem"];

export function isOpenState(state: InterviewLinkState): boolean {
  return OPEN_STATES.includes(state);
}

/** The page for an interview link token. */
export function interviewPath(token: string): string {
  return `/interview/${encodeURIComponent(token)}`;
}

/** An interview link page on the site host, optionally with a query string. */
export function isInterviewPath(next: string | null | undefined): next is string {
  return !!next && /^\/interview\/[^/?#\\]+(?:\?[^#\\]*)?$/.test(next);
}

/** Why the last sign-in came back without a session (`?signin=` from /auth/callback). */
export function readSignInProblem(value: string | string[] | undefined): SignInProblem | null {
  const first = Array.isArray(value) ? value[0] : value;
  return first === "cancelled" || first === "failed" ? first : null;
}

export { SIGNIN_PARAM };

/**
 * Where "I need an accommodation" goes: the company's careers page, else its website. S-01 asks
 * for a contact address, which the company profile doesn't have yet; null hides the link.
 */
export function accommodationHref(company: InterviewCompany): string | null {
  return company.careers_url || company.website || null;
}

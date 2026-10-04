import { ApiError, createApiClient, unwrap } from "@fasthyr/api-client";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { cache } from "react";

import { InterviewLinkPage } from "@/components/interview/interview-link-page";
import { type CandidateClaims, candidateFromClaims } from "@/lib/apply/session";
import { env } from "@/lib/env";
import { t } from "@/lib/i18n";
import { type InterviewLink, isOpenState, readSignInProblem } from "@/lib/interview";
import { loadNotices } from "@/lib/notices";
import { supabaseServer } from "@/lib/supabase/server";

interface Params {
  params: Promise<{ token: string }>;
}

/** The session's candidate, if any, and its access token for the API. */
const readCandidate = cache(async () => {
  const supabase = await supabaseServer();
  const { data } = await supabase.auth.getClaims();
  const candidate = candidateFromClaims(data?.claims as CandidateClaims | undefined);
  const accessToken = candidate
    ? (await supabase.auth.getSession()).data.session?.access_token
    : undefined;
  return { candidate, accessToken };
});

// Read once per request for the metadata and the page. Never cached: the state changes.
const loadLink = cache(async (token: string): Promise<InterviewLink> => {
  const { accessToken } = await readCandidate();
  // Sign-in is optional: signed out, the API answers with the sign-in state.
  const api = createApiClient({
    baseUrl: env.apiUrl,
    getAccessToken: accessToken ? async () => accessToken : undefined,
  });
  try {
    return unwrap(
      await api.GET("/v1/candidate/interviews/{token}", {
        params: { path: { token } },
        cache: "no-store",
      }),
    );
  } catch (error) {
    // Unknown tokens, and strings too long to be one.
    if (error instanceof ApiError && (error.status === 404 || error.status === 422)) notFound();
    throw error;
  }
});

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { token } = await params;
  const link = await loadLink(token);
  return {
    title: t("interview.pageTitle", { company: link.company.name }),
    // A personal link: keep it out of search engines and referrers.
    robots: { index: false, follow: false },
    referrer: "no-referrer",
  };
}

// The interview link from the invitation email (S-01, FR-INTV-02): `/interview/{token}`.
export default async function InterviewLinkRoute({
  params,
  searchParams,
}: Params & { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { token } = await params;
  const [link, { candidate }, query] = await Promise.all([
    loadLink(token),
    readCandidate(),
    searchParams,
  ]);
  return (
    <InterviewLinkPage
      token={token}
      link={link}
      notices={isOpenState(link.state) ? await deviceCheckNotices() : null}
      signedInEmail={candidate?.email ?? null}
      signInProblem={link.state === "sign_in" ? readSignInProblem(query.signin) : null}
    />
  );
}

/** The device check's consent texts (COMP-002). A failure shows a message in the check, not an
 * error page: the candidate can still read the link's state. */
async function deviceCheckNotices() {
  try {
    const { interview, biometric } = await loadNotices();
    return { interview, biometric };
  } catch {
    return null;
  }
}

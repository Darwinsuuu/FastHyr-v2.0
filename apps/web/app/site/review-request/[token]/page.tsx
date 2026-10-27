import { ApiError, createApiClient, unwrap } from "@fasthyr/api-client";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { cache } from "react";

import { ReviewRequestPage } from "@/components/review-request/review-request-page";
import { env } from "@/lib/env";
import { t } from "@/lib/i18n";
import type { ReviewLink } from "@/lib/review-request";

interface Params {
  params: Promise<{ token: string }>;
}

// Read once per request for the metadata and the page. Never cached: the state changes.
const loadLink = cache(async (token: string): Promise<ReviewLink> => {
  const api = createApiClient({ baseUrl: env.apiUrl });
  try {
    return unwrap(
      await api.GET("/v1/public/review-requests/{token}", {
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
    title: t("reviewRequest.pageTitle", { company: link.company.name }),
    // A personal link: keep it out of search engines and referrers.
    robots: { index: false, follow: false },
    referrer: "no-referrer",
  };
}

// "Request a human review" from a rejection email (S-03, ADR-015): `/review-request/{token}`.
export default async function ReviewRequestRoute({ params }: Params) {
  const { token } = await params;
  return <ReviewRequestPage token={token} link={await loadLink(token)} />;
}

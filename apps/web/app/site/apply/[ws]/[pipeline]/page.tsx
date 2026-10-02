import { ApiError, createApiClient, unwrap } from "@fasthyr/api-client";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { cache } from "react";

import { ApplyPage } from "@/components/apply/apply-page";
import { parseSource, type PublicPipeline } from "@/lib/apply";
import { type CandidateClaims, candidateFromClaims, readReturn } from "@/lib/apply/session";
import { env } from "@/lib/env";
import { t } from "@/lib/i18n";
import { supabaseServer } from "@/lib/supabase/server";

interface Params {
  params: Promise<{ ws: string; pipeline: string }>;
}

// No sign-in, so a plain client without a token or workspace header.
const publicApi = createApiClient({ baseUrl: env.apiUrl });

// Read once per request for both the metadata and the page. Never cached: the status changes.
const loadPipeline = cache(async (ws: string, slug: string): Promise<PublicPipeline> => {
  try {
    return unwrap(
      await publicApi.GET("/v1/public/pipelines/{workspace_slug}/{pipeline_slug}", {
        params: { path: { workspace_slug: ws, pipeline_slug: slug } },
        cache: "no-store",
      }),
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
});

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { ws, pipeline } = await params;
  const data = await loadPipeline(ws, pipeline);
  return { title: t("apply.pageTitle", { title: data.title, company: data.company.name }) };
}

// The apply link candidates open from a job post (FR-APPLY-01): `/apply/{workspace}/{pipeline}`
// with an optional `?source=` tag.
export default async function Apply({
  params,
  searchParams,
}: Params & { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { ws, pipeline } = await params;
  const data = await loadPipeline(ws, pipeline);
  const query = await searchParams;
  const source = parseSource(query.source);
  // Candidates sign in with Google or Microsoft on this page (APPLY-002); the session is optional.
  const { data: session } = await (await supabaseServer()).auth.getClaims();
  const candidate = candidateFromClaims(session?.claims as CandidateClaims | undefined);
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    const first = Array.isArray(value) ? value[0] : value;
    if (first !== undefined) search.set(key, first);
  }
  return (
    <ApplyPage
      pipeline={data}
      source={source}
      candidate={candidate}
      returning={readReturn(search, candidate !== null)}
    />
  );
}

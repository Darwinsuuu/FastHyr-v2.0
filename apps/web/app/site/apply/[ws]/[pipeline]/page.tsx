import { ApiError, createApiClient, unwrap } from "@fasthyr/api-client";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { cache } from "react";

import { ApplyPage } from "@/components/apply/apply-page";
import { parseSource, type PublicPipeline } from "@/lib/apply";
import { env } from "@/lib/env";
import { t } from "@/lib/i18n";

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
  const source = parseSource((await searchParams).source);
  return <ApplyPage pipeline={data} source={source} />;
}

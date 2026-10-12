import type { Metadata } from "next";

import { RequireAccess } from "@/components/app-shell/require-access";
import { PipelineDetailPage } from "@/components/pipelines/pipeline-detail-page";
import { t } from "@/lib/i18n";

export const metadata: Metadata = { title: t("shell.nav.pipelines") };

// Pipeline details (PIPE-007): the header and tabs, with the tab in `?tab=`.
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <RequireAccess action="view_pipelines">
      <PipelineDetailPage key={id} pipelineId={id} />
    </RequireAccess>
  );
}

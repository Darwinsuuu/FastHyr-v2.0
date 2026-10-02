import type { Metadata } from "next";

import { PagePlaceholder } from "@/components/app-shell/page-placeholder";
import { NewPipelineButton } from "@/components/pipelines/new-pipeline-button";
import { t } from "@/lib/i18n";

export const metadata: Metadata = { title: t("shell.nav.pipelines") };

// Placeholder until PIPE-004 builds this page; the New pipeline wizard (PIPE-002) already works.
export default function Page() {
  return (
    <PagePlaceholder title="shell.nav.pipelines" action="view_pipelines">
      <NewPipelineButton />
    </PagePlaceholder>
  );
}

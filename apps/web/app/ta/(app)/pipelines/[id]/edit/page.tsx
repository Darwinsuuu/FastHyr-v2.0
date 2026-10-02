import type { Metadata } from "next";

import { RequireAccess } from "@/components/app-shell/require-access";
import { PipelineWizardPage } from "@/components/pipelines/pipeline-wizard";
import { t } from "@/lib/i18n";

export const metadata: Metadata = { title: t("pipelines.wizard.editTitle") };

// A draft, or a scheduled pipeline before it opens, back in the wizard (PIPE-002).
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <RequireAccess action="edit_pipelines">
      <PipelineWizardPage key={id} pipelineId={id} />
    </RequireAccess>
  );
}

import type { Metadata } from "next";

import { RequireAccess } from "@/components/app-shell/require-access";
import { PipelineWizardPage } from "@/components/pipelines/pipeline-wizard";
import { t } from "@/lib/i18n";

export const metadata: Metadata = { title: t("pipelines.wizard.newTitle") };

// New pipeline wizard (frame NewPipeline, PIPE-002). The first save moves to /pipelines/{id}/edit.
export default function Page() {
  return (
    <RequireAccess action="edit_pipelines">
      <PipelineWizardPage />
    </RequireAccess>
  );
}

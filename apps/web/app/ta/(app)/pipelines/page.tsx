import type { Metadata } from "next";

import { RequireAccess } from "@/components/app-shell/require-access";
import { PipelinesPage } from "@/components/pipelines/pipelines-page";
import { t } from "@/lib/i18n";

export const metadata: Metadata = { title: t("shell.nav.pipelines") };

export default function Page() {
  return (
    <RequireAccess action="view_pipelines">
      <PipelinesPage />
    </RequireAccess>
  );
}

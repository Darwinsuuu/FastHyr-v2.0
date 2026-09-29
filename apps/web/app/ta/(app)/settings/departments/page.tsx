import type { Metadata } from "next";

import { PagePlaceholder } from "@/components/app-shell/page-placeholder";
import { t } from "@/lib/i18n";

export const metadata: Metadata = { title: t("shell.nav.departments") };

// Placeholder until WS-002 builds this page.
export default function Page() {
  return <PagePlaceholder title="shell.nav.departments" action="manage_workspace" />;
}

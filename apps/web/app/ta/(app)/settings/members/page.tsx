import type { Metadata } from "next";

import { PagePlaceholder } from "@/components/app-shell/page-placeholder";
import { t } from "@/lib/i18n";

export const metadata: Metadata = { title: t("shell.nav.members") };

// Placeholder until WS-003 builds this page.
export default function Page() {
  return <PagePlaceholder title="shell.nav.members" action="manage_workspace" />;
}

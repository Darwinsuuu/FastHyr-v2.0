import type { Metadata } from "next";

import { PagePlaceholder } from "@/components/app-shell/page-placeholder";
import { t } from "@/lib/i18n";

export const metadata: Metadata = { title: t("shell.nav.creditUsage") };

// Placeholder until BILL-006 builds this page.
export default function Page() {
  return <PagePlaceholder title="shell.nav.creditUsage" action="view_credit_usage" />;
}

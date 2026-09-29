import type { Metadata } from "next";

import { GettingStartedPlaceholder } from "@/app/ta/(app)/getting-started/placeholder";
import { t } from "@/lib/i18n";

export const metadata: Metadata = { title: t("shell.nav.gettingStarted") };

// Where a new workspace opens (FR-AUTH-05). DASH-002 replaces this with the GettingStarted frame.
export default function GettingStartedPage() {
  return <GettingStartedPlaceholder />;
}

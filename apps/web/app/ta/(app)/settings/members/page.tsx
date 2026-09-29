import type { Metadata } from "next";

import { RequireAccess } from "@/components/app-shell/require-access";
import { t } from "@/lib/i18n";

import { MembersPage } from "./members-page";

export const metadata: Metadata = { title: t("shell.nav.members") };

export default function Page() {
  return (
    <RequireAccess action="manage_workspace">
      <MembersPage />
    </RequireAccess>
  );
}

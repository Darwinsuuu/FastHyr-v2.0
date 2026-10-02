import type { Metadata } from "next";

import { RequireAccess } from "@/components/app-shell/require-access";
import { t } from "@/lib/i18n";

import { CompanyProfilePage } from "./company-profile-page";

export const metadata: Metadata = { title: t("shell.nav.company") };

export default function Page() {
  return (
    <RequireAccess action="manage_workspace">
      <CompanyProfilePage />
    </RequireAccess>
  );
}

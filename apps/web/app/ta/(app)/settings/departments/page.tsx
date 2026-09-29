import type { Metadata } from "next";

import { RequireAccess } from "@/components/app-shell/require-access";
import { t } from "@/lib/i18n";

import { DepartmentsPage } from "./departments-page";

export const metadata: Metadata = { title: t("shell.nav.departments") };

export default function Page() {
  return (
    <RequireAccess action="manage_workspace">
      <DepartmentsPage />
    </RequireAccess>
  );
}

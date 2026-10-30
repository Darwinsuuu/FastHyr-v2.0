import type { Metadata } from "next";

import { RequireAccess } from "@/components/app-shell/require-access";
import { EmailTemplatesPage } from "@/components/email-templates/email-templates-page";
import { t } from "@/lib/i18n";

export const metadata: Metadata = { title: t("shell.nav.emailTemplates") };

export default function Page() {
  return (
    <RequireAccess action="manage_email_templates">
      <EmailTemplatesPage />
    </RequireAccess>
  );
}

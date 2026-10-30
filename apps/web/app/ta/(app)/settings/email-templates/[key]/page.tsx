import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { RequireAccess } from "@/components/app-shell/require-access";
import { TemplateEditorPage } from "@/components/email-templates/template-editor-page";
import { isTemplateKey } from "@/lib/email-templates";
import { t } from "@/lib/i18n";

type Props = { params: Promise<{ key: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { key } = await params;
  return {
    title: isTemplateKey(key)
      ? t(`emailTemplates.templates.${key}.name`)
      : t("shell.nav.emailTemplates"),
  };
}

export default async function Page({ params }: Props) {
  const { key } = await params;
  if (!isTemplateKey(key)) notFound();
  return (
    <RequireAccess action="manage_email_templates">
      <TemplateEditorPage templateKey={key} />
    </RequireAccess>
  );
}

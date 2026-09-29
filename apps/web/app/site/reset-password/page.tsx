import type { Metadata } from "next";

import { ResetPasswordForm } from "@/app/site/reset-password/reset-password-form";
import { AuthSplitLayout } from "@/components/auth/auth-split-layout";
import { t } from "@/lib/i18n";
import { supabaseServer } from "@/lib/supabase/server";

export const metadata: Metadata = { title: t("auth.reset.title") };

// Set a new password (S-05, FR-AUTH-02). The reset link signs the user in through /auth/confirm;
// without that session, or when the link failed, the page offers a new link.
export default async function ResetPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  const { data } = await (await supabaseServer()).auth.getClaims();
  return (
    <AuthSplitLayout>
      <ResetPasswordForm linkValid={!error && !!data?.claims} />
    </AuthSplitLayout>
  );
}

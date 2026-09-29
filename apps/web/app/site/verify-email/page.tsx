import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { VerifyEmailPanel } from "@/app/site/verify-email/verify-email-panel";
import { AuthSplitLayout } from "@/components/auth/auth-split-layout";
import { continuePath } from "@/lib/auth/flow";
import { t } from "@/lib/i18n";
import { supabaseServer } from "@/lib/supabase/server";

export const metadata: Metadata = { title: t("auth.verify.pageTitle") };

type Claims = { email?: string; user_metadata?: { email_verified?: boolean } };

// Verify your email (S-06, FR-AUTH-03). Reached after signing up with email + password, or signing
// in before verifying. The address comes from the session if there is one, else from the tab.
export default async function VerifyEmailPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const next = (await searchParams).next ?? null;
  const { data } = await (await supabaseServer()).auth.getClaims();
  const claims = data?.claims as Claims | undefined;
  if (claims && claims.user_metadata?.email_verified !== false) {
    redirect(continuePath(next));
  }
  return (
    <AuthSplitLayout>
      <VerifyEmailPanel next={next} sessionEmail={claims?.email ?? null} />
    </AuthSplitLayout>
  );
}

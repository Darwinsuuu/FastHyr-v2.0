import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { ContinueToApp } from "@/app/site/auth/continue/continue-to-app";
import { t } from "@/lib/i18n";
import { supabaseServer } from "@/lib/supabase/server";

export const metadata: Metadata = { title: t("auth.continuing") };

// Every sign-in method ends here; the client decides where the user lands (FR-AUTH-04).
export default async function ContinuePage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const { next } = await searchParams;
  const { data } = await (await supabaseServer()).auth.getClaims();
  if (!data?.claims) {
    redirect(next ? `/login?next=${encodeURIComponent(next)}` : "/login");
  }
  // Only reachable if email confirmation is ever turned off: an unverified email + password
  // account can't use or join a workspace until it verifies (FR-AUTH-03).
  const metadata = data.claims.user_metadata as { email_verified?: boolean } | undefined;
  if (metadata?.email_verified === false) {
    redirect(next ? `/verify-email?next=${encodeURIComponent(next)}` : "/verify-email");
  }
  return <ContinueToApp next={next ?? null} />;
}

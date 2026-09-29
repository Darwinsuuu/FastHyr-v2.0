import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { type LoginNotice, LoginForm } from "@/app/site/login/login-form";
import { AuthSplitLayout } from "@/components/auth/auth-split-layout";
import { continuePath, isOAuthProvider } from "@/lib/auth/flow";
import { t } from "@/lib/i18n";
import { supabaseServer } from "@/lib/supabase/server";

export const metadata: Metadata = { title: t("auth.signInTitle") };

type Search = { next?: string; error?: string; provider?: string };

function noticeFrom({ error, provider }: Search): LoginNotice | null {
  if (error === "cancelled" && isOAuthProvider(provider)) return { kind: "cancelled", provider };
  if (error === "link-expired") return { kind: "linkExpired" };
  if (error) return { kind: "failed" };
  return null;
}

// Employer sign-in (frame EmployerLogin, FR-AUTH-01). Signed-in visitors go straight on.
export default async function LoginPage({ searchParams }: { searchParams: Promise<Search> }) {
  const search = await searchParams;
  const next = search.next ?? null;
  const { data } = await (await supabaseServer()).auth.getClaims();
  if (data?.claims) {
    redirect(continuePath(next));
  }
  return (
    <AuthSplitLayout>
      <LoginForm next={next} notice={noticeFrom(search)} />
    </AuthSplitLayout>
  );
}

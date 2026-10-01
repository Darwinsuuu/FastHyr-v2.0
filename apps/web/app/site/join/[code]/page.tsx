import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { JoinInvite } from "@/app/site/join/[code]/join-invite";
import { WorkspaceSelectShell } from "@/components/auth/workspace-select-shell";
import { ApiProvider } from "@/lib/api/provider";
import { isVerified, type SessionClaims, userFromClaims } from "@/lib/auth/claims";
import { t } from "@/lib/i18n";
import { supabaseServer } from "@/lib/supabase/server";

export const metadata: Metadata = { title: t("join.pageTitle") };

// Join a workspace from an invite link (S-04, FR-AUTH-06). `code` is the invite code or the link
// token from the invite email; the API tells them apart.
export default async function JoinPage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;
  const here = `/join/${encodeURIComponent(code)}`;
  const { data } = await (await supabaseServer()).auth.getClaims();
  if (!data?.claims) {
    redirect(`/login?next=${encodeURIComponent(here)}`);
  }
  const claims = data.claims as unknown as SessionClaims;
  if (!isVerified(claims)) {
    redirect(`/verify-email?next=${encodeURIComponent(here)}`);
  }
  const user = userFromClaims(claims);
  return (
    <ApiProvider>
      <WorkspaceSelectShell user={user}>
        <JoinInvite inviteKey={code} email={user.email} returnPath={here} />
      </WorkspaceSelectShell>
    </ApiProvider>
  );
}

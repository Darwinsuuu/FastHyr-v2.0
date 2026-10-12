import type { Metadata } from "next";

import { RequireAccess } from "@/components/app-shell/require-access";
import { CandidateProfilePage } from "@/components/candidates/candidate-profile-page";
import { t } from "@/lib/i18n";

export const metadata: Metadata = { title: t("shell.nav.candidates") };

// The candidate profile (ASMT-004): one application of one person, with the tab in `?tab=`.
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ candidateId: string }>;
  searchParams: Promise<{ application?: string | string[] }>;
}) {
  const { candidateId } = await params;
  const { application } = await searchParams;
  const applicationId = typeof application === "string" && application ? application : null;
  return (
    <RequireAccess action="view_candidates">
      <CandidateProfilePage
        key={`${candidateId}-${applicationId}`}
        candidateId={candidateId}
        applicationId={applicationId}
      />
    </RequireAccess>
  );
}

"use client";

import {
  ArrowLeftIcon,
  ArrowRightIcon,
  DotsThreeVerticalIcon,
  DownloadSimpleIcon,
  EnvelopeSimpleIcon,
  FlagIcon,
  XIcon,
} from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type ReactNode, useCallback } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { ProfileOverview } from "@/components/candidates/profile-overview";
import { ProfileRecording } from "@/components/candidates/profile-recording";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button, IconButton } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Menu } from "@/components/ui/menu";
import { Skeleton } from "@/components/ui/skeleton";
import { StagePill } from "@/components/ui/status-pill";
import { Tabs } from "@/components/ui/tabs";
import { ApiError, api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import {
  type ApplicationProfile,
  PROFILE_TABS,
  type ProfileTab,
  parseProfileTab,
  parseSeek,
  profileActions,
  profileHref,
} from "@/lib/candidates/profile";
import { cn } from "@/lib/cn";
import { plural, t } from "@/lib/i18n";
import { can } from "@/lib/permissions";
import { candidatesHref } from "@/lib/pipelines/candidates";
import { longDate, sourceLabel } from "@/lib/pipelines/detail";

const FIT_PILL = {
  strong: "border-evergreen bg-evergreen text-on-evergreen",
  good: "border-evergreen-soft bg-evergreen-soft text-evergreen",
};

const FIT_DOT = {
  strong: "bg-on-evergreen",
  good: "bg-evergreen",
};

/** The candidate profile (frame CandidateProfile, FR-ASMT-07): the header and the tabs, with
 * the tab and a moment in the recording in the URL (`?tab=`, `&t=` seconds). Hiring managers
 * read only. */
export function CandidateProfilePage({
  candidateId,
  applicationId,
}: {
  candidateId: string;
  applicationId: string | null;
}) {
  const { workspace } = useShell();
  const router = useRouter();
  const searchParams = useSearchParams();
  const tab = parseProfileTab(searchParams.get("tab"));
  const seek = parseSeek(searchParams.get("t"));

  const query = useQuery({
    queryKey: keys.application(workspace.id, applicationId ?? ""),
    queryFn: async () =>
      unwrap(
        await api.GET("/v1/applications/{application_id}", {
          params: { path: { application_id: applicationId ?? "" } },
        }),
      ),
    enabled: Boolean(applicationId),
  });

  const go = useCallback(
    (next: ProfileTab, seconds?: number) => {
      if (!applicationId) return;
      const href = profileHref(candidateId, applicationId, next, seconds);
      // A jump to a moment is its own history entry; switching tabs isn't.
      if (seconds !== undefined) router.push(href, { scroll: false });
      else router.replace(href, { scroll: false });
    },
    [router, candidateId, applicationId],
  );

  const profile = query.data;
  // The URL names both; a mismatched pair is a broken link, not another person's profile.
  const mismatch = profile !== undefined && profile.candidate.id !== candidateId;
  if (!applicationId || query.isError || mismatch) {
    const notFound =
      !applicationId || mismatch || (query.error instanceof ApiError && query.error.status === 404);
    return (
      <Page>
        <div className="rounded-lg border border-line bg-surface-raised">
          <EmptyState
            title={t(
              notFound ? "candidates.profile.notFoundTitle" : "candidates.profile.loadFailed",
            )}
            description={notFound ? t("candidates.profile.notFoundBody") : undefined}
          />
        </div>
      </Page>
    );
  }
  if (!profile) return <ProfileSkeleton />;

  const decide = can(workspace.role, "decide_candidates");
  const actions = profileActions(profile, decide);
  return (
    <Page bottomBar={decide}>
      <div className="flex flex-col gap-3">
        <Link
          href={candidatesHref(profile.pipeline.id)}
          className="inline-flex min-h-11 items-center gap-1.5 self-start text-[14px] font-semibold text-ink-muted hover:text-ink md:min-h-0"
        >
          <ArrowLeftIcon aria-hidden="true" className="size-4" />
          {t("candidates.profile.back", { pipeline: profile.pipeline.title })}
        </Link>
        <Header profile={profile} actions={actions} decide={decide} />
      </div>
      <Tabs
        label={t("candidates.profile.tabsLabel")}
        value={tab}
        onValueChange={(value) => go(parseProfileTab(value))}
        items={PROFILE_TABS.map((value) => ({
          value,
          label: t(`candidates.profile.tabs.${value}`),
          content:
            value === "overview" ? (
              <ProfileOverview
                profile={profile}
                onSeek={(ms) => go("interview", Math.floor(ms / 1000))}
                onResume={() => go("resume")}
              />
            ) : value === "interview" ? (
              <ProfileRecording profile={profile} seconds={seek} />
            ) : (
              <div className="rounded-lg border border-line bg-surface-raised">
                <EmptyState
                  title={t("candidates.profile.comingSoonTitle")}
                  description={t("candidates.profile.comingSoon.resume")}
                />
              </div>
            ),
        }))}
      />
      {decide && <BottomBar profile={profile} actions={actions} />}
    </Page>
  );
}

function Page({ children, bottomBar = false }: { children: ReactNode; bottomBar?: boolean }) {
  return (
    <div
      className={cn(
        "page-gutter flex flex-col gap-5 py-6 md:gap-6 md:py-8 lg:px-10 lg:py-9",
        // Room for the phone's sticky action bar.
        bottomBar && "pb-28 md:pb-8",
      )}
    >
      {children}
    </div>
  );
}

function Header({
  profile,
  actions,
  decide,
}: {
  profile: ApplicationProfile;
  actions: ReturnType<typeof profileActions>;
  decide: boolean;
}) {
  const { candidate } = profile;
  const others = profile.history.length;
  return (
    <header className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between xl:gap-6">
      <div className="flex min-w-0 items-start gap-3.5 md:gap-4 xl:min-w-[24rem] xl:flex-1">
        <Avatar id={candidate.id} name={candidate.name} size="lg" />
        <div className="flex min-w-0 flex-col gap-2">
          <h1 className="type-heading break-words">{candidate.name}</h1>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[14px] text-ink-muted">
            <a
              href={`mailto:${candidate.email}`}
              className="min-w-0 break-all text-ink-muted hover:text-ink hover:underline"
            >
              {candidate.email}
            </a>
            <span aria-hidden="true" className="hidden sm:inline">
              ·
            </span>
            <span>
              {t("candidates.profile.applied", {
                date: longDate(new Date(profile.applied_at), profile.timezone),
                source: sourceLabel(profile.source),
              })}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {profile.flagged ? (
              <Badge tone="gap" icon={<FlagIcon aria-hidden="true" weight="bold" />}>
                {plural("candidates.profile.flagged", profile.open_flags)}
              </Badge>
            ) : (
              <StagePill stage={profile.stage} />
            )}
            {profile.fit && profile.stage !== "rejected" && (
              <span
                className={cn(
                  "inline-flex h-7 items-center gap-1.5 rounded-pill border px-2.5 text-[13px] font-[650] whitespace-nowrap",
                  FIT_PILL[profile.fit],
                )}
              >
                <span
                  aria-hidden="true"
                  className={cn("size-2 rounded-pill", FIT_DOT[profile.fit])}
                />
                {t(`pipelines.candidates.fit.${profile.fit}.label`)}
              </span>
            )}
            {profile.review_requested && (
              <Badge tone="watch" className="text-ink">
                {t("candidates.profile.reviewRequested")}
              </Badge>
            )}
            {others > 1 && (
              <a
                href="#profile-history"
                className="text-[14px] font-semibold text-evergreen hover:underline"
              >
                {plural("candidates.profile.applications", others, {
                  workspace: profile.workspace_name,
                })}
              </a>
            )}
          </div>
        </div>
      </div>
      {/* Deciders get the phone's sticky bar instead; Hiring managers only read. */}
      <div
        className={cn(
          "flex-wrap items-center gap-2.5 xl:justify-end",
          decide ? "hidden md:flex" : "flex",
        )}
      >
        {actions.email && (
          <Button
            variant="secondary"
            icon={<EnvelopeSimpleIcon aria-hidden="true" className="size-5" />}
            onClick={() => {
              window.location.href = `mailto:${candidate.email}`;
            }}
          >
            {t("candidates.profile.actions.email")}
          </Button>
        )}
        {/* The report and its progress window arrive with ASMT-009. */}
        <Button
          variant="secondary"
          icon={<DownloadSimpleIcon aria-hidden="true" className="size-5" />}
          disabled
          title={t("candidates.profile.actions.reportSoon")}
        >
          {t("candidates.profile.actions.report")}
        </Button>
        {/* The advance and reject dialogs arrive with ASMT-007. */}
        {actions.reject && (
          <Button
            variant="secondary"
            destructive
            icon={<XIcon aria-hidden="true" className="size-5" />}
            disabled
            title={t("candidates.profile.actions.decideSoon")}
          >
            {t("candidates.profile.actions.reject")}
          </Button>
        )}
        {actions.advance && (
          <Button
            icon={<ArrowRightIcon aria-hidden="true" className="size-5" />}
            disabled
            title={t("candidates.profile.actions.decideSoon")}
          >
            {t("candidates.profile.actions.advance")}
          </Button>
        )}
      </div>
    </header>
  );
}

/** Phones (RESPONSIVE.md): Advance, Reject and More in a bar fixed to the bottom. */
function BottomBar({
  profile,
  actions,
}: {
  profile: ApplicationProfile;
  actions: ReturnType<typeof profileActions>;
}) {
  return (
    <div
      role="toolbar"
      aria-label={t("candidates.profile.actions.label")}
      className="fixed inset-x-0 bottom-0 z-30 flex items-center gap-2 border-t border-line bg-surface-raised px-4 py-3 md:hidden"
    >
      {actions.advance && (
        <Button className="flex-1" disabled title={t("candidates.profile.actions.decideSoon")}>
          {t("candidates.profile.actions.advance")}
        </Button>
      )}
      {actions.reject && (
        <Button
          variant="secondary"
          destructive
          className="flex-1"
          disabled
          title={t("candidates.profile.actions.decideSoon")}
        >
          {t("candidates.profile.actions.reject")}
        </Button>
      )}
      {!actions.advance && !actions.reject && <span className="flex-1" />}
      <Menu
        title={profile.candidate.name}
        trigger={
          <IconButton
            label={t("candidates.profile.actions.more")}
            icon={<DotsThreeVerticalIcon weight="bold" className="size-5" />}
            className="border border-line-strong"
          />
        }
        items={[
          {
            label: t("candidates.profile.actions.email"),
            icon: <EnvelopeSimpleIcon aria-hidden="true" className="size-4" />,
            onSelect: () => {
              window.location.href = `mailto:${profile.candidate.email}`;
            },
          },
          {
            label: t("candidates.profile.actions.report"),
            icon: <DownloadSimpleIcon aria-hidden="true" className="size-4" />,
            disabled: true,
            onSelect: () => {},
          },
        ]}
      />
    </div>
  );
}

function ProfileSkeleton() {
  return (
    <Page>
      <Skeleton className="h-5 w-56" />
      <div className="flex items-start gap-4">
        <Skeleton className="size-14 rounded-pill" />
        <div className="flex flex-1 flex-col gap-3">
          <Skeleton className="h-9 w-64 max-w-full" />
          <Skeleton className="h-5 w-[380px] max-w-full" />
          <Skeleton className="h-7 w-48" />
        </div>
      </div>
      <Skeleton className="h-11 w-full" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-[260px] rounded-lg" />
        <Skeleton className="h-[260px] rounded-lg" />
      </div>
    </Page>
  );
}

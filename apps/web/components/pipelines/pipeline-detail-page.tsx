"use client";

import { ArrowLeftIcon, DotsThreeVerticalIcon, LinkSimpleIcon } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type ReactNode, type RefObject, useEffect, useRef } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { usePipelineActions } from "@/components/pipelines/pipeline-actions";
import { PipelineCandidatesTab } from "@/components/pipelines/pipeline-candidates";
import { PipelineDashboardTab } from "@/components/pipelines/pipeline-dashboard";
import { Avatar } from "@/components/ui/avatar";
import { Button, IconButton } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Menu, type MenuEntry } from "@/components/ui/menu";
import { Skeleton } from "@/components/ui/skeleton";
import { PipelineStatusPill } from "@/components/ui/status-pill";
import { Tabs } from "@/components/ui/tabs";
import { ApiError, api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { t } from "@/lib/i18n";
import { can } from "@/lib/permissions";
import {
  headerMenuFor,
  isLifecycleAction,
  type LifecycleAction,
  type PipelineSummary,
} from "@/lib/pipelines/actions";
import {
  DETAIL_TABS,
  type DetailTab,
  openedLabel,
  type PipelineDetail,
  parseTab,
  tabHref,
} from "@/lib/pipelines/detail";
import { actionHref, DESTRUCTIVE_ACTIONS, PENDING_ACTIONS } from "@/lib/pipelines/list";

/** Pipeline details (frame PipelineView, FR-PIPE-11): the header and the tabs. The Dashboard
 * tab is PIPE-007 and Candidates PIPE-008; Ask Ava (AVA-002) and Setup (PIPE-009) fill in later. */
export function PipelineDetailPage({ pipelineId }: { pipelineId: string }) {
  const { workspace } = useShell();
  const router = useRouter();
  const searchParams = useSearchParams();
  const tab = parseTab(searchParams.get("tab"));

  const query = useQuery({
    queryKey: keys.pipeline(workspace.id, pipelineId),
    queryFn: async () =>
      unwrap(
        await api.GET("/v1/pipelines/{pipeline_id}", {
          params: { path: { pipeline_id: pipelineId } },
        }),
      ),
  });
  const pipeline = query.data;
  // A draft has no details yet: it belongs in the wizard.
  const toWizard = pipeline?.status === "draft" && can(workspace.role, "edit_pipelines");
  useEffect(() => {
    if (toWizard) router.replace(`/pipelines/${encodeURIComponent(pipelineId)}/edit`);
  }, [toWizard, router, pipelineId]);
  // The candidate count on the tab comes from the dashboard, which the Dashboard tab reads too.
  const dashboard = useQuery({
    queryKey: keys.pipelineDashboard(workspace.id, pipelineId),
    queryFn: async () =>
      unwrap(
        await api.GET("/v1/pipelines/{pipeline_id}/dashboard", {
          params: { path: { pipeline_id: pipelineId } },
        }),
      ),
    enabled: Boolean(pipeline) && !toWizard,
  });
  const actions = usePipelineActions({
    timeZone: dashboard.data?.timezone ?? "UTC",
    onArchived: () => router.push("/pipelines"),
  });

  if (query.isError) {
    const notFound = query.error instanceof ApiError && query.error.status === 404;
    return (
      <Page>
        <BackLink />
        <div className="rounded-lg border border-line bg-surface-raised">
          <EmptyState
            title={t(notFound ? "pipelines.detail.notFoundTitle" : "pipelines.detail.loadFailed")}
            description={notFound ? t("pipelines.detail.notFoundBody") : undefined}
          />
        </div>
      </Page>
    );
  }
  if (!pipeline || toWizard) return <HeaderSkeleton />;

  const candidates = dashboard.data?.kpis.candidates;
  return (
    <Page>
      <div className="flex flex-col gap-3">
        <BackLink />
        <Header
          pipeline={pipeline}
          timeZone={dashboard.data?.timezone}
          actions={
            dashboard.data && (
              <ActionsMenu
                summary={{
                  ...pipeline,
                  candidates: dashboard.data.kpis.candidates,
                  to_review: dashboard.data.kpis.ready_for_review,
                }}
                archived={Boolean(pipeline.archived_at)}
                onAction={actions.run}
              />
            )
          }
        />
      </div>
      <Tabs
        label={t("pipelines.detail.tabsLabel")}
        value={tab}
        onValueChange={(value) => {
          // Keep the tab in the URL so links and a refresh land on it.
          router.replace(tabHref(pipelineId, parseTab(value)), { scroll: false });
        }}
        items={DETAIL_TABS.map((value) => ({
          value,
          label: t(`pipelines.detail.tabs.${value}`),
          count: value === "candidates" && candidates !== undefined ? candidates : undefined,
          content:
            value === "dashboard" ? (
              <PipelineDashboardTab pipeline={pipeline} query={dashboard} />
            ) : value === "candidates" ? (
              <PipelineCandidatesTab pipelineId={pipeline.id} />
            ) : (
              <ComingSoon tab={value} />
            ),
        }))}
      />
      {actions.dialogs}
    </Page>
  );
}

function Page({ children }: { children: ReactNode }) {
  return (
    <div className="page-gutter flex flex-col gap-5 py-6 md:gap-6 md:py-8 lg:px-10 lg:py-9">
      {children}
    </div>
  );
}

function BackLink() {
  return (
    <Link
      href="/pipelines"
      className="inline-flex min-h-11 items-center gap-1.5 self-start text-[14px] font-semibold text-ink-muted hover:text-ink md:min-h-0"
    >
      <ArrowLeftIcon aria-hidden="true" className="size-4" />
      {t("pipelines.detail.back")}
    </Link>
  );
}

function Header({
  pipeline,
  timeZone,
  actions,
}: {
  pipeline: PipelineDetail;
  timeZone?: string;
  actions?: ReactNode;
}) {
  const owner = pipeline.owner;
  const ownerName = owner?.name || owner?.email;
  const opened = timeZone ? openedLabel(pipeline, timeZone) : null;
  const facts = [
    pipeline.department?.name ?? t("pipelines.list.noDepartment"),
    pipeline.interview_format && t(`pipelines.detail.formats.${pipeline.interview_format}`),
    opened,
  ].filter((fact): fact is string => Boolean(fact));
  return (
    <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between md:gap-6">
      <div className="flex min-w-0 flex-col gap-2.5">
        <h1 className="type-heading break-words">
          {pipeline.title || t("pipelines.list.untitled")}
        </h1>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[14px] text-ink-muted xl:gap-x-2">
          <PipelineStatusPill
            status={pipeline.status}
            closedOnSchedule={pipeline.closed_reason === "schedule"}
          />
          {facts.map((fact) => (
            <span key={fact} className="inline-flex items-center gap-2">
              <span aria-hidden="true" className="hidden xl:inline">
                ·
              </span>
              {fact}
            </span>
          ))}
          {owner && ownerName && (
            <span className="inline-flex items-center gap-2">
              <span aria-hidden="true" className="hidden xl:inline">
                ·
              </span>
              <span
                className="inline-flex items-center gap-1.5"
                title={t("pipelines.detail.ownedBy", { name: ownerName })}
              >
                <Avatar id={owner.user_id} name={ownerName} src={owner.avatar_url} size="sm" />
                <span className="sr-only">
                  {t("pipelines.detail.ownedBy", { name: ownerName })}
                </span>
                <span aria-hidden="true">{ownerName}</span>
              </span>
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2 self-start md:self-auto">
        {/* The share window (8 sources, posting hints) arrives with PIPE-006. */}
        <Button
          variant="secondary"
          icon={<LinkSimpleIcon aria-hidden="true" className="size-5" />}
          disabled
          title={t("pipelines.detail.shareSoon")}
        >
          {t("pipelines.detail.share")}
        </Button>
        {actions}
      </div>
    </header>
  );
}

/** Pause, close, duplicate and the rest for this pipeline (PIPE-005), as on the list's row. */
function ActionsMenu({
  summary,
  archived,
  onAction,
}: {
  summary: PipelineSummary;
  archived: boolean;
  onAction: (
    action: LifecycleAction,
    summary: PipelineSummary,
    returnFocusTo: RefObject<HTMLButtonElement | null>,
  ) => void;
}) {
  const router = useRouter();
  const { workspace } = useShell();
  const trigger = useRef<HTMLButtonElement>(null);
  const entries = headerMenuFor(summary.status, archived, (action) => can(workspace.role, action));
  if (entries.length === 0) return null;
  const items: MenuEntry[] = entries.map((entry) => {
    if (entry === "separator") return "separator";
    const href = actionHref(entry, summary.id);
    return {
      label: t(`pipelines.list.actions.${entry}`),
      destructive: DESTRUCTIVE_ACTIONS.includes(entry),
      // Copy apply link arrives with PIPE-006 and Top up with BILL-006.
      disabled: PENDING_ACTIONS.includes(entry),
      onSelect: () => {
        if (href) router.push(href);
        else if (isLifecycleAction(entry)) onAction(entry, summary, trigger);
      },
    };
  });
  return (
    <Menu
      title={summary.title || t("pipelines.list.untitled")}
      trigger={
        <IconButton
          ref={trigger}
          // Outlined like the Share button beside it.
          className="border border-line-strong bg-surface-raised text-ink hover:border-ink"
          label={t("pipelines.actions.moreActions")}
          icon={<DotsThreeVerticalIcon weight="bold" className="size-5" />}
        />
      }
      items={items}
    />
  );
}

function ComingSoon({ tab }: { tab: Exclude<DetailTab, "dashboard" | "candidates"> }) {
  return (
    <div className="rounded-lg border border-line bg-surface-raised">
      <EmptyState
        title={t("pipelines.detail.comingSoonTitle")}
        description={t(`pipelines.detail.comingSoon.${tab}`)}
      />
    </div>
  );
}

function HeaderSkeleton() {
  return (
    <Page>
      <Skeleton className="h-5 w-32" />
      <div className="flex flex-col gap-3">
        <Skeleton className="h-9 w-80 max-w-full" />
        <Skeleton className="h-5 w-[420px] max-w-full" />
      </div>
      <Skeleton className="h-11 w-full" />
      <Skeleton className="h-[220px] rounded-lg md:h-[236px] xl:h-[118px]" />
    </Page>
  );
}

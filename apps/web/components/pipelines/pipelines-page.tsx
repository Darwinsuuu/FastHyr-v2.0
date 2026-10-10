"use client";

import { DotsThreeVerticalIcon, ShieldCheckIcon } from "@phosphor-icons/react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { FlowBand } from "@/components/charts/flow-band";
import { NewPipelineButton } from "@/components/pipelines/new-pipeline-button";
import { Avatar } from "@/components/ui/avatar";
import { IconButton } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { SearchInput } from "@/components/ui/input";
import { Menu, type MenuEntry } from "@/components/ui/menu";
import { Pagination } from "@/components/ui/pagination";
import { SegmentedControl } from "@/components/ui/segmented-control";
import { Skeleton } from "@/components/ui/skeleton";
import { PipelineStatusPill } from "@/components/ui/status-pill";
import { type Column, Table } from "@/components/ui/table";
import { api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { plural, t } from "@/lib/i18n";
import { can } from "@/lib/permissions";
import {
  actionHref,
  creditPercent,
  creditTone,
  DESTRUCTIVE_ACTIONS,
  type Emphasis,
  greetingKey,
  hasEnded,
  menuForRole,
  PAGE_SIZES,
  type PageSize,
  PIPELINE_TABS,
  type PipelineListItem,
  type PipelineTab,
  remaining,
} from "@/lib/pipelines/list";

type Range = "week" | "month";

const EMPHASIS: Record<Emphasis, string> = {
  normal: "text-ink",
  soon: "font-[650] text-signal-watch",
  blocked: "font-[650] text-signal-gap",
  upcoming: "font-[650] text-signal-strong",
  muted: "text-ink-muted",
};

const CREDIT_TEXT = {
  normal: "text-ink",
  low: "text-signal-watch",
  out: "text-signal-gap",
  muted: "text-ink-muted",
};

const CREDIT_BAR = {
  normal: "bg-evergreen",
  low: "bg-signal-watch",
  out: "bg-signal-gap",
  muted: "bg-chart-muted",
};

/** The Pipelines page (frame PipelinesV2, FR-PIPE-08): a greeting with what's waiting, how
 * candidates are moving, and every pipeline the member can see, needing attention first. */
export function PipelinesPage() {
  const { user, workspace } = useShell();
  const [tab, setTab] = useState<PipelineTab>("live");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<PageSize>(10);
  const [range, setRange] = useState<Range>("week");
  // Fixed per mount so every row compares against the same moment.
  const [now] = useState(() => new Date());
  const q = useDebouncedValue(search.trim());

  const params = { tab, q, page, pageSize };
  const query = useQuery({
    queryKey: keys.pipelineList(workspace.id, params),
    queryFn: async () =>
      unwrap(
        await api.GET("/v1/pipelines", {
          params: { query: { tab, q: q || undefined, page, page_size: pageSize } },
        }),
      ),
    placeholderData: keepPreviousData,
  });
  const data = query.data;
  const timeZone = data?.timezone ?? "UTC";
  const firstName = user.name.trim().split(/\s+/)[0] || user.name;

  const columns: Column<PipelineListItem>[] = [
    {
      key: "pipeline",
      header: t("pipelines.list.columns.pipeline"),
      cell: (item) => <PipelineCell item={item} />,
    },
    {
      key: "candidates",
      header: t("pipelines.list.columns.candidates"),
      className: "w-[150px]",
      cell: (item) => <CandidatesCell item={item} />,
    },
    {
      key: "credits",
      header: t("pipelines.list.columns.credits"),
      showFrom: "lg",
      className: "w-[170px]",
      cell: (item) => <CreditsCell item={item} />,
    },
    {
      key: "remaining",
      header: t("pipelines.list.columns.remaining"),
      className: "w-[150px] whitespace-nowrap",
      cell: (item) => <RemainingText item={item} now={now} timeZone={timeZone} />,
    },
  ];

  const empty =
    data && data.counts.all === 0 ? (
      <EmptyState
        title={t("pipelines.list.emptyTitle")}
        description={t("pipelines.list.emptyBody")}
      />
    ) : (
      <p className="px-5 py-10 text-center text-[15px] text-ink-muted">
        {q ? t("pipelines.list.noMatches", { query: q }) : t(`pipelines.list.emptyTab.${tab}`)}
      </p>
    );

  return (
    <div className="page-gutter flex flex-col gap-6 py-6 md:gap-8 md:py-10 lg:px-10 lg:py-9">
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between md:gap-6">
        <div className="flex max-w-[720px] flex-col gap-2">
          <p className="type-label text-evergreen uppercase">
            {t("pipelines.list.eyebrow", {
              date: new Intl.DateTimeFormat("en-GB", {
                weekday: "long",
                day: "numeric",
                month: "long",
              }).format(now),
            })}
          </p>
          <h1 className="type-heading">
            {t(`pipelines.list.greeting.${greetingKey(now)}`, { name: firstName })}{" "}
            {data &&
              (data.to_review > 0 ? (
                <span className="text-persimmon-ink">
                  {plural("pipelines.list.readyForYou", data.to_review)}
                </span>
              ) : (
                <span className="text-ink-muted">{t("pipelines.list.nothingWaiting")}</span>
              ))}
          </h1>
          <p className="type-body text-ink-muted">{t("pipelines.list.intro")}</p>
        </div>
        <NewPipelineButton />
      </header>

      <FlowSummary range={range} onRangeChange={setRange} />

      <section aria-labelledby="pipelines-list-heading" className="flex flex-col gap-4">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-col gap-0.5">
            <h2 id="pipelines-list-heading" className="type-title">
              {t("pipelines.list.listTitle")}
            </h2>
            <p className="text-[14px] text-ink-muted">{t("pipelines.list.listHint")}</p>
          </div>
          <div className="flex flex-col gap-3 md:flex-row md:items-center">
            <SegmentedControl
              label={t("pipelines.list.tabsLabel")}
              value={tab}
              onValueChange={(value) => {
                setTab(value);
                setPage(1);
              }}
              // Four tabs with counts don't fit a phone side by side; they scroll instead.
              className="shrink-0 self-start md:self-auto"
              options={PIPELINE_TABS.map((value) => ({
                value,
                label: t(`pipelines.list.tabs.${value}`),
                count: data?.counts[value],
              }))}
            />
            <Field
              label={t("pipelines.list.searchLabel")}
              hideLabel
              className="md:min-w-[200px] md:flex-1 xl:w-[260px] xl:flex-none"
            >
              <SearchInput
                value={search}
                placeholder={t("pipelines.list.search")}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(1);
                }}
              />
            </Field>
          </div>
        </div>

        {query.isError ? (
          <div className="rounded-lg border border-line bg-surface-raised">
            <EmptyState title={t("pipelines.list.loadFailed")} />
          </div>
        ) : !data ? (
          <LoadingRows />
        ) : (
          <Table
            caption={t("pipelines.list.listTitle")}
            className={cn(query.isPlaceholderData && "opacity-70 transition-opacity")}
            rows={data.items}
            columns={columns}
            rowKey={(item) => item.id}
            card={(item) => <PipelineCard item={item} now={now} timeZone={timeZone} />}
            rowMenu={(item) => <RowMenu item={item} />}
            empty={empty}
            footer={
              data.total > 0 && (
                <Pagination
                  total={data.total}
                  page={page}
                  pageSize={pageSize}
                  pageSizes={[...PAGE_SIZES]}
                  onPageChange={setPage}
                  onPageSizeChange={(size) => {
                    setPageSize(size as PageSize);
                    setPage(1);
                  }}
                  noun={plural("pipelines.list.noun", data.total)}
                />
              )
            }
          />
        )}
      </section>
    </div>
  );
}

/** How candidates are moving. Zeros until the analytics endpoint arrives (DASH-003). */
function FlowSummary({
  range,
  onRangeChange,
}: {
  range: Range;
  onRangeChange: (range: Range) => void;
}) {
  const title = t("pipelines.list.flowTitle");
  return (
    <section
      aria-labelledby="pipelines-flow-heading"
      className="flex flex-col gap-5 rounded-lg border border-line bg-surface-raised p-4 md:p-6"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-0.5 sm:flex-row sm:items-baseline sm:gap-3">
          <h2 id="pipelines-flow-heading" className="type-title">
            {title}
          </h2>
          <span className="text-[14px] text-ink-muted">{t("pipelines.list.flowScope")}</span>
        </div>
        <SegmentedControl
          label={t("pipelines.list.timeRange")}
          size="sm"
          value={range}
          onValueChange={onRangeChange}
          options={[
            { value: "week", label: t("pipelines.list.thisWeek") },
            { value: "month", label: t("pipelines.list.last30Days") },
          ]}
        />
      </div>
      <FlowBand
        title={title}
        stages={[
          { label: t("pipelines.list.flowApplied"), value: 0 },
          { label: t("pipelines.list.flowInvited"), value: 0 },
          { label: t("pipelines.list.flowInterviewed"), value: 0 },
          { label: t("pipelines.list.flowReady"), value: 0 },
        ]}
      />
      <div className="flex flex-col gap-2 border-t border-line pt-4 text-[14px] text-ink-muted md:flex-row md:items-center md:justify-between">
        <p>{t("pipelines.list.flowSoon")}</p>
        <p className="flex items-center gap-2">
          <ShieldCheckIcon aria-hidden="true" className="size-4 shrink-0 text-evergreen" />
          {t("pipelines.list.fairnessNote")}
        </p>
      </div>
    </section>
  );
}

function LoadingRows() {
  return (
    <div className="flex flex-col divide-y divide-line rounded-md border border-line bg-surface-raised">
      {Array.from({ length: 5 }, (_, index) => (
        <div key={index} className="flex items-center gap-3 p-4">
          <Skeleton className="size-9 rounded-pill" />
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-4 w-48 max-w-full" />
            <Skeleton className="h-3.5 w-32" />
          </div>
        </div>
      ))}
    </div>
  );
}

const titleOf = (item: PipelineListItem) => item.title || t("pipelines.list.untitled");

function OwnerAvatar({ item }: { item: PipelineListItem }) {
  const owner = item.owner;
  const name = owner?.name || owner?.email || "?";
  return (
    <span title={owner ? t("pipelines.list.ownedBy", { name }) : undefined}>
      <Avatar id={owner?.user_id ?? item.id} name={name} src={owner?.avatar_url} />
    </span>
  );
}

function PipelineCell({ item }: { item: PipelineListItem }) {
  const ended = hasEnded(item.status);
  return (
    <div className="flex min-w-0 items-center gap-3">
      <OwnerAvatar item={item} />
      <div className="flex min-w-0 flex-col gap-1">
        <Link
          href={actionHref(item.status === "draft" ? "continueSetup" : "open", item.id) ?? "#"}
          className={cn(
            "truncate font-semibold hover:text-persimmon-ink hover:underline",
            ended ? "text-ink-muted" : "text-ink",
          )}
        >
          {titleOf(item)}
        </Link>
        <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-[13px] leading-[18px] text-ink-muted">
          <span className="truncate">
            {item.department?.name ?? t("pipelines.list.noDepartment")}
          </span>
          <PipelineStatusPill
            status={item.status}
            closedOnSchedule={item.closed_reason === "schedule"}
          />
        </div>
      </div>
    </div>
  );
}

function CandidatesCell({ item }: { item: PipelineListItem }) {
  if (item.status === "scheduled" || item.status === "draft") {
    return <span className="text-[14px] text-ink-muted">{t("pipelines.list.notOpenYet")}</span>;
  }
  return (
    <div className="flex flex-col gap-0.5">
      <span
        className={cn(
          "font-semibold tabular-nums",
          hasEnded(item.status) ? "text-ink-muted" : "text-ink",
        )}
      >
        {formatNumber(item.candidates)}
      </span>
      {item.to_review > 0 && (
        <Link
          href={actionHref("open", item.id) ?? "#"}
          className="text-[13px] leading-[18px] font-semibold text-persimmon-ink hover:underline"
        >
          {t("pipelines.list.toReview", { count: formatNumber(item.to_review) })}
        </Link>
      )}
    </div>
  );
}

function CreditsCell({ item }: { item: PipelineListItem }) {
  const tone = creditTone(item);
  const used = formatNumber(item.credits_used);
  const total = formatNumber(item.credits_reserved);
  return (
    <div className="flex flex-col gap-1.5">
      <span className={cn("text-[14px] tabular-nums", CREDIT_TEXT[tone])}>
        <strong className="font-semibold">{used}</strong> / {total}
      </span>
      <div
        role="img"
        aria-label={t("pipelines.list.creditsLabel", { used, total })}
        className="h-1.5 w-full max-w-[140px] overflow-hidden rounded-pill bg-surface-sunk"
      >
        <div
          className={cn("h-full rounded-pill", CREDIT_BAR[tone])}
          style={{ width: `${creditPercent(item)}%` }}
        />
      </div>
    </div>
  );
}

function RemainingText({
  item,
  now,
  timeZone,
}: {
  item: PipelineListItem;
  now: Date;
  timeZone: string;
}) {
  const { label, emphasis } = remaining(item, now, timeZone);
  return <span className={cn("text-[14px]", EMPHASIS[emphasis])}>{label}</span>;
}

/** Phone layout (RESPONSIVE.md): title, status, candidates and days remaining. */
function PipelineCard({
  item,
  now,
  timeZone,
}: {
  item: PipelineListItem;
  now: Date;
  timeZone: string;
}) {
  return (
    <div className="flex flex-col gap-3">
      <PipelineCell item={item} />
      <dl className="grid grid-cols-2 gap-3 pl-12 text-[13px] leading-[18px]">
        <div className="flex flex-col gap-0.5">
          <dt className="text-ink-muted">{t("pipelines.list.columns.candidates")}</dt>
          <dd>
            <CandidatesCell item={item} />
          </dd>
        </div>
        <div className="flex flex-col gap-0.5">
          <dt className="text-ink-muted">{t("pipelines.list.columns.remaining")}</dt>
          <dd>
            <RemainingText item={item} now={now} timeZone={timeZone} />
          </dd>
        </div>
      </dl>
    </div>
  );
}

function RowMenu({ item }: { item: PipelineListItem }) {
  const router = useRouter();
  const { workspace } = useShell();
  const title = titleOf(item);
  const entries = menuForRole(item.status, (action) => can(workspace.role, action));
  if (entries.length === 0) return <span className="inline-flex size-11 md:size-9" />;
  const items: MenuEntry[] = entries.map((entry) => {
    if (entry === "separator") return "separator";
    const href = actionHref(entry, item.id);
    return {
      label: t(`pipelines.list.actions.${entry}`),
      destructive: DESTRUCTIVE_ACTIONS.includes(entry),
      // Pause, close and the other lifecycle actions arrive with PIPE-005, Copy apply link
      // with PIPE-006 and Top up with BILL-006; until then they show but can't be picked.
      disabled: href === null,
      onSelect: () => {
        if (href) router.push(href);
      },
    };
  });
  return (
    <Menu
      title={title}
      trigger={
        <IconButton
          label={t("pipelines.list.actionsFor", { title })}
          icon={<DotsThreeVerticalIcon weight="bold" className="size-5" />}
          className="md:size-9"
        />
      }
      items={items}
    />
  );
}

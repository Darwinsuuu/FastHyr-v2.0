"use client";

import {
  ArrowRightIcon,
  DotsThreeVerticalIcon,
  DownloadSimpleIcon,
  EnvelopeSimpleIcon,
  FileTextIcon,
  FlagIcon,
  UserIcon,
  XIcon,
} from "@phosphor-icons/react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { type ReactNode, useState } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { IconButton } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { SearchInput } from "@/components/ui/input";
import { Menu, type MenuEntry } from "@/components/ui/menu";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { StagePill } from "@/components/ui/status-pill";
import { type Column, Table } from "@/components/ui/table";
import { Tooltip } from "@/components/ui/tooltip";
import { api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { plural, t } from "@/lib/i18n";
import { access, can } from "@/lib/permissions";
import {
  appliedLabel,
  CANDIDATE_PAGE_SIZES,
  type CandidateAction,
  candidateActionHref,
  type CandidateFilter,
  candidateMenu,
  type CandidatePageSize,
  filtersFor,
  fitExplanation,
  parseFilter,
  POLL_MS,
  type PipelineCandidate,
  type PipelineCandidates,
  shouldPoll,
} from "@/lib/pipelines/candidates";
import { sourceLabel } from "@/lib/pipelines/detail";

const ACTION_ICONS: Record<CandidateAction, ReactNode> = {
  profile: <UserIcon aria-hidden="true" className="size-4" />,
  resume: <FileTextIcon aria-hidden="true" className="size-4" />,
  report: <DownloadSimpleIcon aria-hidden="true" className="size-4" />,
  reviewFlag: <FlagIcon aria-hidden="true" className="size-4" />,
  email: <EnvelopeSimpleIcon aria-hidden="true" className="size-4" />,
  advance: <ArrowRightIcon aria-hidden="true" className="size-4" />,
  reject: <XIcon aria-hidden="true" className="size-4" />,
};

/** The Candidates tab (frame PipelineView, FR-PIPE-12/13, A-02, A-03): stage filters with
 * counts, search and every candidate with their stage, fit, source and when they applied.
 * Hiring managers see the shortlist only, and no decisions. */
export function PipelineCandidatesTab({ pipelineId }: { pipelineId: string }) {
  const { workspace } = useShell();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const shortlist = access(workspace.role, "view_candidates") === "shortlist";
  const filter = parseFilter(searchParams.get("stage"), shortlist);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<CandidatePageSize>(10);
  const q = useDebouncedValue(search.trim());

  const params = { stage: filter, q, page, pageSize };
  const query = useQuery({
    queryKey: keys.pipelineCandidates(workspace.id, pipelineId, params),
    queryFn: async () =>
      unwrap(
        await api.GET("/v1/pipelines/{pipeline_id}/applications", {
          params: {
            path: { pipeline_id: pipelineId },
            query: { stage: filter, q: q || undefined, page, page_size: pageSize },
          },
        }),
      ),
    placeholderData: keepPreviousData,
    // Screening, interviews and scoring move people along on their own.
    refetchInterval: (current) => (shouldPoll(current.state.data?.counts) ? POLL_MS : false),
  });
  const data = query.data;

  const pickFilter = (next: CandidateFilter) => {
    const nextParams = new URLSearchParams(searchParams.toString());
    if (next === "all") nextParams.delete("stage");
    else nextParams.set("stage", next);
    router.replace(`${pathname}?${nextParams.toString()}`, { scroll: false });
    setPage(1);
  };

  return (
    <section aria-label={t("pipelines.candidates.caption")} className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between xl:gap-6">
        <FilterChips
          filters={filtersFor(shortlist)}
          value={filter}
          counts={data?.counts}
          onChange={pickFilter}
        />
        <Field
          label={t("pipelines.candidates.searchLabel")}
          hideLabel
          className="w-full md:max-w-[320px] xl:w-[260px] xl:shrink-0"
        >
          <SearchInput
            value={search}
            placeholder={t("pipelines.candidates.search")}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
          />
        </Field>
      </div>
      {shortlist && (
        <p className="text-[14px] text-ink-muted">{t("pipelines.candidates.shortlistNote")}</p>
      )}
      {query.isError ? (
        <div className="rounded-md border border-line bg-surface-raised">
          <EmptyState title={t("pipelines.candidates.loadFailed")} />
        </div>
      ) : !data ? (
        <LoadingRows />
      ) : (
        <CandidatesTable
          data={data}
          filter={filter}
          query={q}
          page={page}
          pageSize={pageSize}
          stale={query.isPlaceholderData}
          onPageChange={setPage}
          onPageSizeChange={(size) => {
            setPageSize(size);
            setPage(1);
          }}
        />
      )}
    </section>
  );
}

function FilterChips({
  filters,
  value,
  counts,
  onChange,
}: {
  filters: readonly CandidateFilter[];
  value: CandidateFilter;
  counts?: PipelineCandidates["counts"];
  onChange: (filter: CandidateFilter) => void;
}) {
  return (
    // A long set of chips scrolls inside its own bar on phones (RESPONSIVE.md §3).
    <div
      role="group"
      aria-label={t("pipelines.candidates.filtersLabel")}
      className="-mx-4 flex gap-1.5 overflow-x-auto px-4 pb-1 md:mx-0 md:flex-wrap md:overflow-visible md:px-0 md:pb-0"
    >
      {filters.map((filter) => {
        const pressed = filter === value;
        const flag = filter === "flagged";
        return (
          <button
            key={filter}
            type="button"
            aria-pressed={pressed}
            onClick={() => onChange(filter)}
            className={cn(
              "inline-flex h-11 shrink-0 items-center gap-2 rounded-pill border px-3 text-[13px] font-semibold whitespace-nowrap transition-colors md:h-9",
              pressed
                ? "border-evergreen bg-evergreen text-on-evergreen"
                : flag
                  ? "border-signal-gap bg-surface-raised text-signal-gap hover:bg-surface-sunk"
                  : "border-line bg-surface-raised text-ink hover:border-line-strong",
            )}
          >
            {flag && <FlagIcon aria-hidden="true" weight="bold" className="size-3.5" />}
            {t(`pipelines.candidates.filters.${filter}`)}
            <span
              className={cn(
                "font-mono text-[12px] font-medium tabular-nums",
                pressed ? "text-evergreen-soft" : "text-ink-muted",
              )}
            >
              {counts ? formatNumber(counts[filter]) : "…"}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function CandidatesTable({
  data,
  filter,
  query,
  page,
  pageSize,
  stale,
  onPageChange,
  onPageSizeChange,
}: {
  data: PipelineCandidates;
  filter: CandidateFilter;
  query: string;
  page: number;
  pageSize: CandidatePageSize;
  stale: boolean;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: CandidatePageSize) => void;
}) {
  const timeZone = data.timezone;
  const columns: Column<PipelineCandidate>[] = [
    {
      key: "candidate",
      header: t("pipelines.candidates.columns.candidate"),
      cell: (item) => <CandidateCell item={item} />,
    },
    {
      key: "stage",
      header: t("pipelines.candidates.columns.stage"),
      className: "w-[200px]",
      cell: (item) => <StageCell item={item} />,
    },
    {
      key: "status",
      header: t("pipelines.candidates.columns.status"),
      className: "w-[140px]",
      cell: (item) => <FitCell item={item} passMark={data.pass_mark} />,
    },
    {
      key: "source",
      header: t("pipelines.candidates.columns.source"),
      showFrom: "xl",
      className: "w-[130px]",
      cell: (item) => <span className="text-[14px]">{sourceLabel(item.source)}</span>,
    },
    {
      key: "applied",
      header: t("pipelines.candidates.columns.applied"),
      showFrom: "xl",
      className: "w-[120px] whitespace-nowrap",
      cell: (item) => <AppliedCell item={item} timeZone={timeZone} />,
    },
  ];

  const empty =
    data.counts.all === 0 ? (
      <EmptyState
        title={t("pipelines.candidates.emptyTitle")}
        description={t("pipelines.candidates.emptyBody")}
      />
    ) : (
      <p className="px-5 py-10 text-center text-[15px] text-ink-muted">
        {query
          ? t("pipelines.candidates.noMatches", { query })
          : t("pipelines.candidates.emptyFilter")}
      </p>
    );

  return (
    <Table
      caption={
        filter === "all"
          ? t("pipelines.candidates.caption")
          : `${t("pipelines.candidates.caption")}: ${t(`pipelines.candidates.filters.${filter}`)}`
      }
      className={cn(stale && "opacity-70 transition-opacity")}
      rows={data.items}
      columns={columns}
      rowKey={(item) => item.id}
      card={(item) => <CandidateCard item={item} passMark={data.pass_mark} timeZone={timeZone} />}
      rowMenu={(item) => <RowMenu item={item} />}
      empty={empty}
      footer={
        data.total > 0 && (
          <Pagination
            total={data.total}
            page={page}
            pageSize={pageSize}
            pageSizes={[...CANDIDATE_PAGE_SIZES]}
            onPageChange={onPageChange}
            onPageSizeChange={(size) => onPageSizeChange(size as CandidatePageSize)}
            noun={plural("pipelines.candidates.noun", data.total)}
          />
        )
      }
    />
  );
}

function LoadingRows() {
  return (
    <div className="flex flex-col divide-y divide-line rounded-md border border-line bg-surface-raised">
      {Array.from({ length: 5 }, (_, index) => (
        <div key={index} className="flex items-center gap-3 p-4">
          <Skeleton className="size-10 rounded-pill" />
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-4 w-48 max-w-full" />
            <Skeleton className="h-3.5 w-56 max-w-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

function CandidateCell({ item }: { item: PipelineCandidate }) {
  const { candidate } = item;
  // The name links to the profile once ASMT-004 builds it.
  return (
    <div className="flex min-w-0 items-center gap-3">
      <Avatar id={candidate.id} name={candidate.name} />
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="truncate text-[15px] leading-[22px] font-[650] text-ink">
          {candidate.name}
        </span>
        <span className="truncate text-[13px] leading-[18px] text-ink-muted">
          {candidate.email}
        </span>
      </div>
    </div>
  );
}

function StageCell({ item }: { item: PipelineCandidate }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {item.flagged ? (
        // Flagged stands in for Ready for review / Didn't pass until a person resolves it.
        <Badge tone="gap" icon={<FlagIcon aria-hidden="true" weight="bold" />}>
          {t("pipelines.candidates.flagged")}
        </Badge>
      ) : (
        <StagePill stage={item.stage} />
      )}
      {item.review_requested && (
        <Badge tone="watch" className="text-ink">
          {t("pipelines.candidates.reviewRequested")}
        </Badge>
      )}
    </div>
  );
}

const FIT_PILL = {
  strong: "border-evergreen bg-evergreen text-on-evergreen",
  good: "border-evergreen-soft bg-evergreen-soft text-evergreen",
};

const FIT_DOT = {
  strong: "bg-on-evergreen",
  good: "bg-evergreen",
};

function FitCell({ item, passMark }: { item: PipelineCandidate; passMark?: number | null }) {
  const fit = fitExplanation(item, passMark);
  if (!fit || !item.fit) {
    return (
      <span className="text-[14px] text-ink-muted">
        <span aria-hidden="true" title={t("pipelines.candidates.noStatusHint")}>
          {t("pipelines.candidates.noStatus")}
        </span>
        <span className="sr-only">{t("pipelines.candidates.noStatusHint")}</span>
      </span>
    );
  }
  return (
    <Tooltip
      side="bottom"
      content={
        <span className="flex max-w-[260px] flex-col gap-1.5 py-1">
          <span className="text-[14px] font-bold">{fit.label}</span>
          <span className="font-normal">{fit.description}</span>
          <span className="border-t border-surface-raised/25 pt-1.5 text-[12px] leading-[17px] font-normal">
            {fit.why}
          </span>
        </span>
      }
    >
      <button
        type="button"
        aria-label={`${fit.label}. ${fit.description} ${fit.why}`}
        className={cn(
          "inline-flex h-7 cursor-help items-center gap-1.5 rounded-pill border px-2.5 text-[13px] font-[650] whitespace-nowrap",
          FIT_PILL[item.fit],
        )}
      >
        <span aria-hidden="true" className={cn("size-2 rounded-pill", FIT_DOT[item.fit])} />
        {fit.label}
      </button>
    </Tooltip>
  );
}

function AppliedCell({ item, timeZone }: { item: PipelineCandidate; timeZone: string }) {
  const { date, time } = appliedLabel(item.applied_at, timeZone);
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[14px] text-ink">{date}</span>
      <span className="text-[12px] text-ink-muted">{time}</span>
    </div>
  );
}

/** Phone layout (RESPONSIVE.md): name and email, stage, fit, and when they applied. */
function CandidateCard({
  item,
  passMark,
  timeZone,
}: {
  item: PipelineCandidate;
  passMark?: number | null;
  timeZone: string;
}) {
  const { date } = appliedLabel(item.applied_at, timeZone);
  return (
    <div className="flex flex-col gap-3">
      <CandidateCell item={item} />
      <div className="flex flex-col gap-2 pl-[52px]">
        <div className="flex flex-wrap items-center gap-1.5">
          <StageCell item={item} />
          {item.fit && item.stage !== "rejected" && <FitCell item={item} passMark={passMark} />}
        </div>
        <span className="text-[13px] leading-[18px] text-ink-muted">
          {sourceLabel(item.source)} · {date}
        </span>
      </div>
    </div>
  );
}

function RowMenu({ item }: { item: PipelineCandidate }) {
  const { workspace } = useShell();
  const name = item.candidate.name;
  const entries = candidateMenu(item, {
    decide: can(workspace.role, "decide_candidates"),
    resolve: can(workspace.role, "resolve_reviews"),
  });
  const items: MenuEntry[] = entries.map((entry) => {
    if (entry === "separator") return "separator";
    const href = candidateActionHref(entry, item);
    return {
      label: t(`pipelines.candidates.actions.${entry}`),
      icon: ACTION_ICONS[entry],
      destructive: entry === "reject",
      // The profile, flag review, downloads and the advance and reject dialogs arrive with
      // ASMT-004, ASMT-003, ASMT-009 and ASMT-007; until then they show but can't be picked.
      disabled: href === null,
      onSelect: () => {
        if (href) window.location.href = href;
      },
    };
  });
  return (
    <Menu
      title={name}
      trigger={
        <IconButton
          label={t("pipelines.candidates.actionsFor", { name })}
          icon={<DotsThreeVerticalIcon weight="bold" className="size-5" />}
          className="md:size-9"
        />
      }
      items={items}
    />
  );
}

"use client";

import {
  DotsThreeVerticalIcon,
  FunnelSimpleIcon,
  InfoIcon,
  LockSimpleIcon,
  PencilSimpleIcon,
  PlusIcon,
  TrashIcon,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useMemo, useState } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { Avatar, pairIndex } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button, IconButton } from "@/components/ui/button";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input, SearchInput, Textarea } from "@/components/ui/input";
import { Menu } from "@/components/ui/menu";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { type Column, Table } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { Tooltip } from "@/components/ui/tooltip";
import { api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { cn } from "@/lib/cn";
import {
  DESCRIPTION_MAX,
  type DepartmentRow,
  departmentNameError,
  departmentRows,
  NAME_MAX,
  pipelineCount,
  saveErrorKey,
  searchRows,
  summarize,
  type DepartmentList,
} from "@/lib/departments";
import { formatDate, formatNumber } from "@/lib/format";
import { type MessageKey, plural, t } from "@/lib/i18n";

const PAGE_SIZES = [10, 25, 50];
const MAX_AVATARS = 3;

// Colour pairs for the department initial, as in the frame; picked by id so they never shift.
const INITIAL_TONES = [
  "bg-evergreen-soft text-evergreen",
  "bg-persimmon-soft text-persimmon-ink",
  "bg-sage text-ink",
  "bg-surface-sunk text-ink",
];

type Form = { mode: "add" } | { mode: "edit"; row: DepartmentRow & { id: string } };

/** Departments (frame Departments, FR-WS-02): Admins add, rename and delete departments. */
export function DepartmentsPage() {
  const { workspace } = useShell();
  const queryKey = keys.departments(workspace.id);
  const queryClient = useQueryClient();
  const toast = useToast();
  const query = useQuery({
    queryKey,
    queryFn: async () => unwrap(await api.GET("/v1/departments")),
  });

  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZES[0] ?? 10);
  const [form, setForm] = useState<Form | null>(null);
  const [deleting, setDeleting] = useState<(DepartmentRow & { id: string }) | null>(null);

  const rows = useMemo(
    () => (query.data ? departmentRows(query.data, t("departments.noDepartment")) : []),
    [query.data],
  );
  const matches = searchRows(rows, search);
  const start = (Math.min(page, Math.max(1, Math.ceil(matches.length / pageSize))) - 1) * pageSize;
  const shown = matches.slice(start, start + pageSize);
  const colourOf = (id: string | null) =>
    INITIAL_TONES[
      Math.max(
        0,
        rows.findIndex((row) => row.id === id),
      ) % INITIAL_TONES.length
    ];

  const refresh = () => queryClient.invalidateQueries({ queryKey });

  async function remove(row: DepartmentRow & { id: string }) {
    try {
      unwrap(
        await api.DELETE("/v1/departments/{department_id}", {
          params: { path: { department_id: row.id } },
        }),
      );
      toast({ title: t("departments.deleteDialog.deleted", { name: row.name }) });
    } catch {
      toast({ title: t("departments.deleteDialog.failed"), tone: "error" });
    }
    await refresh();
  }

  const columns: Column<DepartmentRow>[] = [
    {
      key: "name",
      header: t("departments.columns.department"),
      cell: (row) => <NameCell row={row} tone={colourOf(row.id)} />,
    },
    {
      key: "pipelines",
      header: t("departments.columns.pipelines"),
      className: "w-[220px]",
      cell: (row) => <PipelinesCell row={row} />,
    },
    {
      key: "candidates",
      header: t("departments.columns.candidates"),
      showFrom: "xl",
      align: "end",
      cell: (row) =>
        row.stats.candidate_count ? formatNumber(row.stats.candidate_count) : <Dash />,
    },
    {
      key: "access",
      header: t("departments.columns.access"),
      showFrom: "lg",
      cell: (row) => <AccessCell row={row} />,
    },
    {
      key: "created",
      header: t("departments.columns.created"),
      showFrom: "xl",
      className: "whitespace-nowrap text-ink-muted",
      cell: (row) =>
        row.createdAt
          ? formatDate(row.createdAt, browserTimeZone())
          : t("departments.builtInShort"),
    },
  ];

  return (
    <div className="page-gutter flex flex-col gap-6 py-6 md:gap-8 md:py-10 lg:px-10 lg:py-9">
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between md:gap-8">
        <div className="flex max-w-[680px] flex-col gap-2">
          <p className="type-label text-evergreen uppercase">{t("departments.eyebrow")}</p>
          <h1 className="type-heading">{t("departments.title")}</h1>
          <p className="type-body text-ink-muted">{t("departments.intro")}</p>
        </div>
        <Button
          icon={<PlusIcon aria-hidden="true" />}
          className="max-md:w-full"
          onClick={() => setForm({ mode: "add" })}
        >
          {t("departments.add")}
        </Button>
      </header>

      {query.isError ? (
        <div className="rounded-lg border border-line bg-surface-raised">
          <EmptyState title={t("departments.loadFailed")} />
        </div>
      ) : (
        <>
          <Summary list={query.data} />

          <section aria-labelledby="departments-heading" className="flex flex-col gap-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <h2 id="departments-heading" className="type-title flex items-center gap-2">
                {t("departments.listTitle")}
                {query.data && (
                  <Badge tone="neutral" className="tabular-nums">
                    {formatNumber(matches.length)}
                  </Badge>
                )}
              </h2>
              <Field label={t("departments.search")} hideLabel className="md:w-[320px]">
                <SearchInput
                  value={search}
                  placeholder={t("departments.search")}
                  onChange={(event) => {
                    setSearch(event.target.value);
                    setPage(1);
                  }}
                />
              </Field>
            </div>

            {query.isPending ? (
              <LoadingRows />
            ) : (
              <Table
                caption={t("departments.listTitle")}
                rows={shown}
                columns={columns}
                rowKey={(row) => row.id ?? "none"}
                card={(row) => <DepartmentCard row={row} tone={colourOf(row.id)} />}
                rowMenu={(row) =>
                  row.id === null ? (
                    <BuiltInLock />
                  ) : (
                    <RowMenu
                      row={{ ...row, id: row.id }}
                      onEdit={(target) => setForm({ mode: "edit", row: target })}
                      onDelete={setDeleting}
                    />
                  )
                }
                empty={
                  <p className="px-5 py-10 text-center text-[15px] text-ink-muted">
                    {t("departments.noMatches", { query: search.trim() })}
                  </p>
                }
                footer={
                  matches.length > 0 && (
                    <Pagination
                      total={matches.length}
                      page={page}
                      pageSize={pageSize}
                      pageSizes={PAGE_SIZES}
                      onPageChange={setPage}
                      onPageSizeChange={(size) => {
                        setPageSize(size);
                        setPage(1);
                      }}
                      noun={plural("departments.noun", matches.length)}
                    />
                  )
                }
              />
            )}
          </section>

          <HowItWorks />
        </>
      )}

      {query.data && form && (
        <DepartmentFormDialog
          key={form.mode === "edit" ? form.row.id : "add"}
          form={form}
          list={query.data}
          onClose={() => setForm(null)}
          onSaved={refresh}
        />
      )}

      <ConfirmDialog
        open={deleting !== null}
        onOpenChange={(open) => !open && setDeleting(null)}
        title={t("departments.deleteDialog.title", { name: deleting?.name ?? "" })}
        description={deleteMessage(deleting)}
        confirmLabel={t("departments.delete")}
        cancelLabel={t("departments.deleteDialog.keep")}
        destructive
        onConfirm={() => (deleting ? remove(deleting) : undefined)}
      >
        <ul className="flex list-disc flex-col gap-1.5 pl-5 text-[15px] leading-6 text-ink">
          <li>{t("departments.deleteDialog.keepResults")}</li>
          <li>{t("departments.deleteDialog.loseAccess")}</li>
        </ul>
      </ConfirmDialog>
    </div>
  );
}

function browserTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

function deleteMessage(row: DepartmentRow | null): string {
  const count = row ? pipelineCount(row.stats) : 0;
  return count
    ? plural("departments.deleteDialog.moves", count)
    : t("departments.deleteDialog.noPipelines");
}

function Dash() {
  return <span className="text-ink-muted">—</span>;
}

function Summary({ list }: { list: DepartmentList | undefined }) {
  const summary = list ? summarize(list) : null;
  const tiles: { label: string; value: string; sub: string }[] = summary
    ? [
        {
          label: t("departments.stats.departments"),
          value: formatNumber(summary.departments),
          sub: t("departments.stats.departmentsSub"),
        },
        {
          label: t("departments.stats.filed"),
          value: t("departments.stats.filedValue", {
            filed: formatNumber(summary.filed),
            total: formatNumber(summary.pipelines),
          }),
          sub: t("departments.stats.filedSub"),
        },
        {
          label: t("departments.stats.noDepartment"),
          value: formatNumber(summary.noDepartment),
          sub: plural("departments.stats.noDepartmentSub", summary.noDepartment),
        },
        {
          label: t("departments.stats.empty"),
          value: formatNumber(summary.empty),
          sub: t("departments.stats.emptySub"),
        },
      ]
    : [];

  return (
    <section
      aria-label={t("departments.summary")}
      className="grid grid-cols-2 overflow-hidden rounded-lg border border-line bg-surface-raised lg:grid-cols-4"
    >
      {(summary ? tiles : Array.from({ length: 4 }, () => null)).map((tile, index) => (
        <div
          key={index}
          className={cn(
            "flex flex-col gap-1 border-line p-4 md:p-5",
            index % 2 === 1 && "border-l",
            index >= 2 && "border-t lg:border-t-0",
            index === 2 && "lg:border-l",
          )}
        >
          {tile ? (
            <>
              <span className="type-label text-ink-muted">{tile.label}</span>
              <span className="font-display text-[26px] leading-8 font-[560] tabular-nums md:text-[30px] md:leading-9">
                {tile.value}
              </span>
              <span className="text-[13px] leading-[18px] text-ink-muted">{tile.sub}</span>
            </>
          ) : (
            <>
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-8 w-16" />
              <Skeleton className="h-3.5 w-28" />
            </>
          )}
        </div>
      ))}
    </section>
  );
}

function LoadingRows() {
  return (
    <div className="flex flex-col divide-y divide-line rounded-md border border-line bg-surface-raised">
      {Array.from({ length: 4 }, (_, index) => (
        <div key={index} className="flex items-center gap-3 p-4">
          <Skeleton className="size-9 rounded-md" />
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3.5 w-64 max-w-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

function DepartmentInitial({ row, tone }: { row: DepartmentRow; tone: string | undefined }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "flex size-9 shrink-0 items-center justify-center rounded-md text-[15px] font-[650]",
        row.id === null ? "border border-dashed border-line-strong text-ink-muted" : tone,
      )}
    >
      {row.id === null ? "–" : row.name.charAt(0).toUpperCase()}
    </span>
  );
}

function rowDescription(row: DepartmentRow): string {
  if (row.id === null) return t("departments.noDepartmentDescription");
  return row.description || t("departments.noDescription");
}

function NameCell({ row, tone }: { row: DepartmentRow; tone: string | undefined }) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <DepartmentInitial row={row} tone={tone} />
      <div className="flex min-w-0 flex-col">
        <span className="flex items-center gap-2">
          <span className="truncate font-semibold text-ink">{row.name}</span>
          {row.id === null && <Badge tone="outline">{t("departments.default")}</Badge>}
        </span>
        <span
          className={cn(
            "truncate text-[13px] leading-[18px] text-ink-muted",
            !row.description && row.id !== null && "italic",
          )}
        >
          {rowDescription(row)}
        </span>
      </div>
    </div>
  );
}

function breakdown(row: DepartmentRow): string {
  const { active, scheduled, closed } = row.stats.pipelines;
  const parts = [
    active && t("departments.breakdown.active", { count: formatNumber(active) }),
    scheduled && t("departments.breakdown.scheduled", { count: formatNumber(scheduled) }),
    closed && t("departments.breakdown.closed", { count: formatNumber(closed) }),
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : t("departments.noneYet");
}

function PipelinesCell({ row }: { row: DepartmentRow }) {
  const total = pipelineCount(row.stats);
  const { active, scheduled, closed } = row.stats.pipelines;
  const width = (count: number) => `${total ? (count / total) * 100 : 0}%`;
  return (
    <div className="flex flex-col gap-1.5">
      <span className="font-semibold tabular-nums">
        {plural("departments.pipelineCount", total)}
      </span>
      <span
        aria-hidden="true"
        className="flex h-1.5 w-full max-w-[160px] overflow-hidden rounded-pill bg-surface-sunk"
      >
        <span className="h-full bg-evergreen" style={{ width: width(active) }} />
        <span className="h-full bg-chart-amber" style={{ width: width(scheduled) }} />
        <span className="h-full bg-line-strong" style={{ width: width(closed) }} />
      </span>
      <span className="text-[13px] leading-[18px] text-ink-muted">{breakdown(row)}</span>
    </div>
  );
}

function accessNote(row: DepartmentRow): string {
  return row.id === null
    ? t("departments.adminsOnly")
    : plural("departments.memberCount", row.stats.members.length);
}

function AccessCell({ row }: { row: DepartmentRow }) {
  const members = row.stats.members;
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex -space-x-1">
        {members.slice(0, MAX_AVATARS).map((member) => {
          const name = member.full_name || t("departments.unnamedMember");
          return (
            <Tooltip key={member.member_id} content={name}>
              <span tabIndex={0} className="inline-flex rounded-pill ring-2 ring-surface-raised">
                <Avatar id={member.user_id} name={name} src={member.avatar_url} size="sm" />
              </span>
            </Tooltip>
          );
        })}
      </span>
      <span className="text-[13px] whitespace-nowrap text-ink-muted">
        {accessNote(row)}
        {members.length > MAX_AVATARS && ` (+${members.length - MAX_AVATARS})`}
      </span>
    </div>
  );
}

/** Phone layout: one card per department. */
function DepartmentCard({ row, tone }: { row: DepartmentRow; tone: string | undefined }) {
  return (
    <div className="flex flex-col gap-3">
      <NameCell row={row} tone={tone} />
      <dl className="grid grid-cols-2 gap-3 pl-12 text-[13px] leading-[18px]">
        <div className="flex flex-col gap-0.5">
          <dt className="text-ink-muted">{t("departments.columns.pipelines")}</dt>
          <dd className="font-semibold text-ink">
            {plural("departments.pipelineCount", pipelineCount(row.stats))}
          </dd>
          <dd className="text-ink-muted">{breakdown(row)}</dd>
        </div>
        <div className="flex flex-col gap-0.5">
          <dt className="text-ink-muted">{t("departments.columns.access")}</dt>
          <dd className="font-semibold text-ink">{accessNote(row)}</dd>
        </div>
      </dl>
    </div>
  );
}

function BuiltInLock() {
  return (
    <Tooltip content={t("departments.builtIn")}>
      <span
        tabIndex={0}
        aria-label={t("departments.builtIn")}
        className="inline-flex size-11 items-center justify-center rounded-[10px] text-ink-muted md:size-9"
      >
        <LockSimpleIcon aria-hidden="true" className="size-4" />
      </span>
    </Tooltip>
  );
}

function RowMenu({
  row,
  onEdit,
  onDelete,
}: {
  row: DepartmentRow & { id: string };
  onEdit: (row: DepartmentRow & { id: string }) => void;
  onDelete: (row: DepartmentRow & { id: string }) => void;
}) {
  const router = useRouter();
  return (
    <Menu
      title={row.name}
      trigger={
        <IconButton
          label={t("departments.actionsFor", { name: row.name })}
          icon={<DotsThreeVerticalIcon weight="bold" className="size-5" />}
          className="md:size-9"
        />
      }
      items={[
        {
          label: t("departments.edit"),
          icon: <PencilSimpleIcon aria-hidden="true" />,
          onSelect: () => onEdit(row),
        },
        {
          label: t("departments.viewPipelines"),
          icon: <FunnelSimpleIcon aria-hidden="true" />,
          // PIPE-004 reads the department filter from the query string.
          onSelect: () => router.push(`/pipelines?department=${row.id}`),
        },
        "separator",
        {
          label: t("departments.delete"),
          icon: <TrashIcon aria-hidden="true" />,
          destructive: true,
          onSelect: () => onDelete(row),
        },
      ]}
    />
  );
}

function HowItWorks() {
  const [before, after] = t("departments.howBody").split("{link}");
  return (
    <section className="flex gap-3 rounded-lg border border-line bg-evergreen-soft/50 p-4 md:p-5">
      <InfoIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-evergreen" />
      <p className="text-[14px] leading-[21px] text-ink">
        <strong className="font-[650]">{t("departments.howTitle")}</strong> {before}
        <Link
          href="/settings/members"
          className="font-semibold text-evergreen underline underline-offset-2"
        >
          {t("departments.howLink")}
        </Link>
        {after}
      </p>
    </section>
  );
}

const FORM_ID = "department-form";

/** Add or edit a department. Mounted per opening, so the fields start from the row being edited. */
function DepartmentFormDialog({
  form,
  list,
  onClose,
  onSaved,
}: {
  form: Form;
  list: DepartmentList;
  onClose: () => void;
  onSaved: () => Promise<unknown>;
}) {
  const toast = useToast();
  const editing = form.mode === "edit" ? form.row : null;
  const [name, setName] = useState(editing?.name ?? "");
  const [description, setDescription] = useState(editing?.description ?? "");
  const [touched, setTouched] = useState(false);
  const [serverError, setServerError] = useState<MessageKey | null>(null);
  const [busy, setBusy] = useState(false);

  const localError = departmentNameError(name, list.departments, editing?.id ?? null);
  const error = serverError ?? (touched ? localError : null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched(true);
    if (localError) return;
    setBusy(true);
    const body = { name: name.trim(), description: description.trim() };
    try {
      const saved = editing
        ? unwrap(
            await api.PATCH("/v1/departments/{department_id}", {
              params: { path: { department_id: editing.id } },
              body,
            }),
          )
        : unwrap(await api.POST("/v1/departments", { body }));
      await onSaved();
      toast({
        title: editing
          ? t("departments.form.saved")
          : t("departments.form.added", { name: saved.name }),
      });
      onClose();
    } catch (failure) {
      const key = saveErrorKey(failure);
      if (key) setServerError(key);
      else toast({ title: t("departments.form.saveFailed"), tone: "error" });
      setBusy(false);
    }
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => !open && onClose()}
      title={t(editing ? "departments.form.editTitle" : "departments.form.addTitle")}
      description={t(editing ? "departments.form.editBody" : "departments.form.addBody")}
      size="sm"
      dismissible={!busy}
      footer={
        <>
          <Button variant="secondary" disabled={busy} onClick={onClose}>
            {t("ui.cancel")}
          </Button>
          <Button type="submit" form={FORM_ID} loading={busy}>
            {editing ? t("departments.form.save") : t("departments.add")}
          </Button>
        </>
      }
    >
      <form
        id={FORM_ID}
        noValidate
        onSubmit={(event) => void submit(event)}
        className="flex flex-col gap-5 pb-2"
      >
        <Field
          label={t("departments.form.name")}
          hint={error ? undefined : t("departments.form.nameHint")}
          error={error ? t(error) : undefined}
          required
        >
          <Input
            value={name}
            maxLength={NAME_MAX}
            placeholder={t("departments.form.namePlaceholder")}
            autoComplete="off"
            onChange={(event) => {
              setName(event.target.value);
              setTouched(true);
              setServerError(null);
            }}
          />
        </Field>
        <Field label={t("departments.form.description")}>
          <Textarea
            value={description}
            rows={3}
            maxLength={DESCRIPTION_MAX}
            placeholder={t("departments.form.descriptionPlaceholder")}
            onChange={(event) => setDescription(event.target.value)}
          />
        </Field>
      </form>
    </Dialog>
  );
}

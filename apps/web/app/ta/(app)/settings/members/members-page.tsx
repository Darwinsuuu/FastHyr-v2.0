"use client";

import {
  CaretDownIcon,
  DotsThreeVerticalIcon,
  PencilSimpleIcon,
  UserMinusIcon,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button, IconButton } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { SearchInput } from "@/components/ui/input";
import { Menu } from "@/components/ui/menu";
import { Pagination } from "@/components/ui/pagination";
import { Popover } from "@/components/ui/popover";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { type Column, Table } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";
import { plural, t } from "@/lib/i18n";
import {
  actionErrorKey,
  canManage,
  departmentsText,
  displayName,
  EDIT_ROLES,
  filterMembers,
  lastActiveText,
  type Member,
  type MemberFilters,
  NO_FILTERS,
  type Role,
  ROLES,
} from "@/lib/members";

const PAGE_SIZES = [10, 25, 50];
const ALL = "all";

interface DepartmentOption {
  id: string;
  name: string;
}

/** Manage members (frame ManageMembers, FR-WS-04/05): who has access, and to which departments. */
export function MembersPage() {
  const { workspace } = useShell();
  const queryKey = keys.members(workspace.id);
  const queryClient = useQueryClient();
  const toast = useToast();
  const query = useQuery({
    queryKey,
    queryFn: async () => unwrap(await api.GET("/v1/members")).members,
  });
  const departmentsQuery = useQuery({
    queryKey: keys.departments(workspace.id),
    queryFn: async () => unwrap(await api.GET("/v1/departments")),
  });
  const departments: DepartmentOption[] = useMemo(
    () => (departmentsQuery.data?.departments ?? []).map(({ id, name }) => ({ id, name })),
    [departmentsQuery.data],
  );

  const [filters, setFilters] = useState<MemberFilters>(NO_FILTERS);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZES[0] ?? 10);
  const [editing, setEditing] = useState<Member | null>(null);
  const [removing, setRemoving] = useState<Member | null>(null);
  // Fixed per render pass so every row compares against the same moment.
  const [now] = useState(() => new Date());
  const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  const members = query.data ?? [];
  const matches = filterMembers(members, filters);
  const start = (Math.min(page, Math.max(1, Math.ceil(matches.length / pageSize))) - 1) * pageSize;
  const shown = matches.slice(start, start + pageSize);

  const updateFilters = (change: Partial<MemberFilters>) => {
    setFilters((current) => ({ ...current, ...change }));
    setPage(1);
  };
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey }),
      // Departments list who can see each department.
      queryClient.invalidateQueries({ queryKey: keys.departments(workspace.id) }),
    ]);

  async function remove(member: Member) {
    try {
      unwrap(
        await api.DELETE("/v1/members/{member_id}", {
          params: { path: { member_id: member.id } },
        }),
      );
      toast({ title: t("members.removeDialog.removed", { name: displayName(member) }) });
    } catch (failure) {
      toast({ title: t(actionErrorKey(failure)), tone: "error" });
    }
    await refresh();
  }

  const columns: Column<Member>[] = [
    {
      key: "member",
      header: t("members.columns.member"),
      cell: (member) => <MemberCell member={member} />,
    },
    {
      key: "role",
      header: t("members.columns.role"),
      className: "w-[170px]",
      cell: (member) => <RoleCell member={member} />,
    },
    {
      key: "departments",
      header: t("members.columns.departments"),
      showFrom: "lg",
      cell: (member) => <DepartmentsCell member={member} />,
    },
    {
      key: "lastActive",
      header: t("members.columns.lastActive"),
      showFrom: "xl",
      className: "whitespace-nowrap text-ink-muted",
      cell: (member) => lastActiveText(member.last_active_at, now, timeZone),
    },
    {
      key: "status",
      header: t("members.columns.status"),
      showFrom: "lg",
      cell: () => <ActivePill />,
    },
  ];

  return (
    <div className="page-gutter flex flex-col gap-6 py-6 md:gap-8 md:py-10 lg:px-10 lg:py-9">
      <header className="flex max-w-[680px] flex-col gap-2">
        <p className="type-label text-evergreen uppercase">{t("members.eyebrow")}</p>
        <h1 className="type-heading">{t("members.title")}</h1>
        <p className="type-body text-ink-muted">{t("members.intro")}</p>
      </header>

      {query.isError ? (
        <div className="rounded-lg border border-line bg-surface-raised">
          <EmptyState title={t("members.loadFailed")} />
        </div>
      ) : (
        <section aria-labelledby="members-heading" className="flex flex-col gap-4">
          <h2 id="members-heading" className="type-title flex items-center gap-2">
            {t("members.tab")}
            {query.data && (
              <Badge tone="evergreen" className="tabular-nums">
                {formatNumber(members.length)}
              </Badge>
            )}
          </h2>

          <div className="flex flex-col gap-3 md:flex-row md:flex-wrap md:items-center">
            <Field label={t("members.searchLabel")} hideLabel className="md:w-[300px]">
              <SearchInput
                value={filters.query}
                placeholder={t("members.search")}
                onChange={(event) => updateFilters({ query: event.target.value })}
              />
            </Field>
            <div className="grid grid-cols-2 gap-3 md:flex">
              <Field label={t("members.roleFilter")} hideLabel className="md:w-[180px]">
                <Select
                  size="sm"
                  className="max-md:h-11"
                  value={filters.role ?? ALL}
                  onValueChange={(value) =>
                    updateFilters({ role: value === ALL ? null : (value as Role) })
                  }
                  options={[
                    { value: ALL, label: t("members.allRoles") },
                    ...ROLES.map((role) => ({ value: role, label: t(`app.role.${role}`) })),
                  ]}
                />
              </Field>
              <DepartmentFilter
                departments={departments}
                value={filters.departmentIds}
                onChange={(departmentIds) => updateFilters({ departmentIds })}
              />
            </div>
            <p className="text-[14px] text-ink-muted tabular-nums md:ml-auto" aria-live="polite">
              {query.data && plural("members.count", matches.length)}
            </p>
          </div>

          {query.isPending ? (
            <LoadingRows />
          ) : (
            <Table
              caption={t("members.tab")}
              rows={shown}
              columns={columns}
              rowKey={(member) => member.id}
              card={(member) => (
                <MemberCard
                  member={member}
                  lastActive={lastActiveText(member.last_active_at, now, timeZone)}
                />
              )}
              rowMenu={(member) =>
                canManage(member) ? (
                  <RowMenu member={member} onEdit={setEditing} onRemove={setRemoving} />
                ) : (
                  <span className="inline-flex size-11 md:size-9" aria-hidden="true" />
                )
              }
              empty={
                <p className="px-5 py-10 text-center text-[15px] text-ink-muted">
                  {t("members.noMatches")}
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
                    noun={plural("members.noun", matches.length)}
                  />
                )
              }
            />
          )}
        </section>
      )}

      <RolesCard />

      {editing && (
        <EditAccessDialog
          key={editing.id}
          member={editing}
          workspaceName={workspace.name}
          departments={departments}
          onClose={() => setEditing(null)}
          onSaved={refresh}
        />
      )}

      <ConfirmDialog
        open={removing !== null}
        onOpenChange={(open) => !open && setRemoving(null)}
        title={t("members.removeDialog.title", { name: removing ? displayName(removing) : "" })}
        description={t("members.removeDialog.body", { workspace: workspace.name })}
        confirmLabel={t("members.remove")}
        destructive
        onConfirm={() => (removing ? remove(removing) : undefined)}
      />
    </div>
  );
}

function LoadingRows() {
  return (
    <div className="flex flex-col divide-y divide-line rounded-md border border-line bg-surface-raised">
      {Array.from({ length: 4 }, (_, index) => (
        <div key={index} className="flex items-center gap-3 p-4">
          <Skeleton className="size-9 rounded-pill" />
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3.5 w-56 max-w-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

function MemberCell({ member }: { member: Member }) {
  const name = displayName(member);
  return (
    <div className="flex min-w-0 items-center gap-3">
      <Avatar id={member.user_id} name={name} src={member.avatar_url} />
      <div className="flex min-w-0 flex-col">
        <span className="truncate font-semibold text-ink">
          {name}
          {member.is_you && <span className="font-normal text-ink-muted"> {t("members.you")}</span>}
        </span>
        {member.email && member.email !== name && (
          <span className="truncate text-[13px] leading-[18px] text-ink-muted">{member.email}</span>
        )}
      </div>
    </div>
  );
}

function RoleCell({ member }: { member: Member }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-semibold">{t(`app.role.${member.role}`)}</span>
      {member.is_owner && (
        <span className="text-[13px] leading-[18px] text-ink-muted">{t("members.owner")}</span>
      )}
    </div>
  );
}

function DepartmentsCell({ member }: { member: Member }) {
  const empty = member.role !== "admin" && member.departments.length === 0;
  return <span className={cn(empty && "text-ink-muted italic")}>{departmentsText(member)}</span>;
}

function ActivePill() {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-pill bg-evergreen-soft px-2.5 py-0.5 text-[13px] font-semibold text-evergreen">
      <span aria-hidden="true" className="size-1.5 rounded-pill bg-evergreen" />
      {t("members.active")}
    </span>
  );
}

/** Phone layout: one card per member. */
function MemberCard({ member, lastActive }: { member: Member; lastActive: string }) {
  return (
    <div className="flex flex-col gap-3">
      <MemberCell member={member} />
      <dl className="grid grid-cols-2 gap-3 pl-12 text-[13px] leading-[18px]">
        <div className="flex flex-col gap-0.5">
          <dt className="text-ink-muted">{t("members.columns.role")}</dt>
          <dd className="font-semibold text-ink">
            {t(`app.role.${member.role}`)}
            {member.is_owner && (
              <span className="block font-normal text-ink-muted">{t("members.owner")}</span>
            )}
          </dd>
        </div>
        <div className="flex flex-col gap-0.5">
          <dt className="text-ink-muted">{t("members.columns.lastActive")}</dt>
          <dd className="text-ink">{lastActive}</dd>
        </div>
        <div className="col-span-2 flex flex-col gap-0.5">
          <dt className="text-ink-muted">{t("members.columns.departments")}</dt>
          <dd className="text-ink">
            <DepartmentsCell member={member} />
          </dd>
        </div>
      </dl>
    </div>
  );
}

function RowMenu({
  member,
  onEdit,
  onRemove,
}: {
  member: Member;
  onEdit: (member: Member) => void;
  onRemove: (member: Member) => void;
}) {
  const name = displayName(member);
  return (
    <Menu
      title={name}
      trigger={
        <IconButton
          label={t("members.actionsFor", { name })}
          icon={<DotsThreeVerticalIcon weight="bold" className="size-5" />}
          className="md:size-9"
        />
      }
      items={[
        {
          label: t("members.edit"),
          icon: <PencilSimpleIcon aria-hidden="true" />,
          onSelect: () => onEdit(member),
        },
        "separator",
        {
          label: t("members.remove"),
          icon: <UserMinusIcon aria-hidden="true" />,
          destructive: true,
          onSelect: () => onRemove(member),
        },
      ]}
    />
  );
}

function DepartmentFilter({
  departments,
  value,
  onChange,
}: {
  departments: DepartmentOption[];
  value: string[];
  onChange: (value: string[]) => void;
}) {
  const selected = departments.filter((d) => value.includes(d.id));
  const label =
    selected.length === 0
      ? t("members.allDepartmentsFilter")
      : selected.length === 1
        ? (selected[0]?.name ?? "")
        : t("members.departmentsSelected");
  return (
    <Popover
      align="start"
      className="p-2"
      trigger={
        <button
          type="button"
          aria-label={`${t("members.departmentFilter")}: ${label}`}
          className="flex h-11 min-w-0 items-center justify-between gap-2 rounded-md border border-line-strong bg-surface-raised px-3 text-left text-[15px] text-ink md:h-10 md:w-[200px] md:text-[14px]"
        >
          <span className="truncate">{label}</span>
          <span className="flex shrink-0 items-center gap-1.5">
            {selected.length > 1 && (
              <Badge tone="evergreen" className="tabular-nums">
                {selected.length}
              </Badge>
            )}
            <CaretDownIcon aria-hidden="true" className="size-4 text-ink-muted" />
          </span>
        </button>
      }
    >
      <div role="group" aria-label={t("members.departmentFilter")} className="flex flex-col">
        {departments.length === 0 ? (
          <p className="px-2 py-3 text-[14px] text-ink-muted">
            {t("members.noDepartmentsToFilter")}
          </p>
        ) : (
          <div className="max-h-[280px] overflow-y-auto px-2">
            {departments.map((department) => (
              <Checkbox
                key={department.id}
                label={department.name}
                checked={value.includes(department.id)}
                onCheckedChange={(checked) =>
                  onChange(
                    checked
                      ? [...value, department.id]
                      : value.filter((id) => id !== department.id),
                  )
                }
              />
            ))}
          </div>
        )}
        {value.length > 0 && (
          <div className="mt-1 border-t border-line pt-1">
            <Button variant="quiet" size="sm" className="w-full" onClick={() => onChange([])}>
              {t("members.clearSelection")}
            </Button>
          </div>
        )}
      </div>
    </Popover>
  );
}

function RolesCard() {
  return (
    <section
      aria-labelledby="roles-heading"
      className="flex flex-col gap-4 rounded-lg border border-line bg-surface-raised p-4 md:p-6"
    >
      <h2 id="roles-heading" className="type-title">
        {t("members.rolesTitle")}
      </h2>
      <dl className="grid gap-4 md:grid-cols-3 md:gap-6">
        {ROLES.map((role) => (
          <div key={role} className="flex flex-col gap-1">
            <dt className="flex items-center gap-2 font-semibold text-ink">
              <span aria-hidden="true" className="size-2 rounded-pill bg-evergreen" />
              {t(`app.role.${role}`)}
            </dt>
            <dd className="text-[14px] leading-[21px] text-ink-muted">
              {t(`members.roles.${role}`)}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

/** Change a member's role and departments. Mounted per opening, so it starts from their access. */
function EditAccessDialog({
  member,
  workspaceName,
  departments,
  onClose,
  onSaved,
}: {
  member: Member;
  workspaceName: string;
  departments: DepartmentOption[];
  onClose: () => void;
  onSaved: () => Promise<unknown>;
}) {
  const toast = useToast();
  const name = displayName(member);
  const [role, setRole] = useState<Role>(member.role);
  const [departmentIds, setDepartmentIds] = useState<string[]>(member.departments.map((d) => d.id));
  const [busy, setBusy] = useState(false);
  const isAdmin = role === "admin";

  async function save() {
    setBusy(true);
    try {
      unwrap(
        await api.PATCH("/v1/members/{member_id}", {
          params: { path: { member_id: member.id } },
          body: { role, department_ids: isAdmin ? [] : departmentIds },
        }),
      );
      await onSaved();
      toast({ title: t("members.editDialog.saved", { name }) });
      onClose();
    } catch (failure) {
      toast({ title: t(actionErrorKey(failure)), tone: "error" });
      setBusy(false);
      await onSaved();
    }
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => !open && onClose()}
      title={t("members.editDialog.title")}
      description={t("members.editDialog.body", { name, workspace: workspaceName })}
      size="md"
      dismissible={!busy}
      footer={
        <>
          <Button variant="secondary" disabled={busy} onClick={onClose}>
            {t("ui.cancel")}
          </Button>
          <Button loading={busy} onClick={() => void save()}>
            {t("members.editDialog.save")}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-5 pb-2">
        <Field
          label={t("members.editDialog.role")}
          hint={t("members.editDialog.roleHint", { role: t(`app.role.${member.role}`) })}
        >
          <Select
            value={role}
            onValueChange={(value) => setRole(value as Role)}
            options={EDIT_ROLES.map((value) => ({ value, label: t(`app.role.${value}`) }))}
          />
        </Field>
        <fieldset className="flex flex-col gap-1.5">
          <legend className="mb-1.5 text-[14px] leading-5 font-semibold text-ink">
            {t("members.editDialog.departments")}
          </legend>
          {isAdmin ? (
            <p className="rounded-md border border-line bg-surface-sunk px-3.5 py-3 text-[15px] text-ink">
              {t("members.allDepartments")}
            </p>
          ) : departments.length === 0 ? (
            <p className="rounded-md border border-dashed border-line-strong px-3.5 py-3 text-[14px] text-ink-muted">
              {t("members.editDialog.noDepartmentsYet")}
            </p>
          ) : (
            <div className="max-h-[240px] overflow-y-auto rounded-md border border-line-strong px-3.5">
              {departments.map((department) => (
                <Checkbox
                  key={department.id}
                  label={department.name}
                  checked={departmentIds.includes(department.id)}
                  onCheckedChange={(checked) =>
                    setDepartmentIds((current) =>
                      checked
                        ? [...current, department.id]
                        : current.filter((id) => id !== department.id),
                    )
                  }
                />
              ))}
            </div>
          )}
          <p className="text-[13px] leading-[18px] text-ink-muted">
            {isAdmin ? t("members.editDialog.adminHint") : t("members.editDialog.departmentsHint")}
          </p>
        </fieldset>
      </div>
    </Dialog>
  );
}

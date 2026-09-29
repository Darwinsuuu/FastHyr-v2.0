"use client";

import { CopyIcon, EnvelopeSimpleIcon } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input, Textarea } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { cn } from "@/lib/cn";
import { env } from "@/lib/env";
import { formatDate } from "@/lib/format";
import { plural, t } from "@/lib/i18n";
import {
  expiresSoon,
  expiryText,
  type Invite,
  inviteActionErrorKey,
  inviteFormError,
  isEmail,
  nextExpiry,
  sentText,
  shareMessage,
} from "@/lib/invites";
import { EDIT_ROLES, type Role } from "@/lib/members";

const PAGE_SIZES = [10, 25, 50];

export interface DepartmentOption {
  id: string;
  name: string;
}

/** Pending invites for the active workspace (Admins only). */
export function useInvites() {
  const { workspace } = useShell();
  return useQuery({
    queryKey: keys.invites(workspace.id),
    queryFn: async () => unwrap(await api.GET("/v1/invites")).invites,
  });
}

function useRefreshInvites() {
  const { workspace } = useShell();
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: keys.invites(workspace.id) });
}

const timeZone = () => Intl.DateTimeFormat().resolvedOptions().timeZone;

/** The Pending invites tab (frame ManageMembers): share, resend or revoke each invite. */
export function PendingInvites({ onShare }: { onShare: (invite: Invite) => void }) {
  const { workspace } = useShell();
  const toast = useToast();
  const refresh = useRefreshInvites();
  const query = useInvites();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZES[0] ?? 10);
  const [resending, setResending] = useState<Invite | null>(null);
  const [revoking, setRevoking] = useState<Invite | null>(null);
  // Fixed per render pass so every row compares against the same moment.
  const [now] = useState(() => new Date());

  if (query.isError) {
    return (
      <div className="rounded-lg border border-line bg-surface-raised">
        <EmptyState title={t("members.invites.loadFailed")} />
      </div>
    );
  }
  if (query.isPending) return <LoadingRows />;

  const invites = query.data;
  const start = (Math.min(page, Math.max(1, Math.ceil(invites.length / pageSize))) - 1) * pageSize;
  const shown = invites.slice(start, start + pageSize);

  async function resend(invite: Invite) {
    try {
      const resent = unwrap(
        await api.POST("/v1/invites/{invite_id}/resend", {
          params: { path: { invite_id: invite.id } },
        }),
      );
      onShare(resent);
    } catch (failure) {
      toast({ title: t(inviteActionErrorKey(failure)), tone: "error" });
    }
    await refresh();
  }

  async function revoke(invite: Invite) {
    try {
      unwrap(
        await api.DELETE("/v1/invites/{invite_id}", {
          params: { path: { invite_id: invite.id } },
        }),
      );
      toast({ title: t("members.invites.revokeDialog.revoked", { email: invite.email }) });
    } catch (failure) {
      toast({ title: t(inviteActionErrorKey(failure)), tone: "error" });
    }
    await refresh();
  }

  return (
    <section
      aria-label={t("members.invites.tab")}
      className="overflow-hidden rounded-lg border border-line bg-surface-raised"
    >
      <div className="flex flex-col gap-1 px-4 py-4 md:flex-row md:items-center md:justify-between md:px-5">
        <p className="text-[14px] text-ink-muted tabular-nums" aria-live="polite">
          {plural("members.invites.count", invites.length)}
        </p>
        <p className="text-[13px] text-ink-muted">{t("members.invites.expiryNote")}</p>
      </div>
      {invites.length === 0 ? (
        <p className="border-t border-line px-5 py-7 text-center text-[14px] text-ink-muted">
          {t("members.invites.empty")}
        </p>
      ) : (
        <ul>
          {shown.map((invite) => (
            <InviteRow
              key={invite.id}
              invite={invite}
              now={now}
              onShare={() => onShare(invite)}
              onResend={() => setResending(invite)}
              onRevoke={() => setRevoking(invite)}
            />
          ))}
        </ul>
      )}
      {invites.length > 0 && (
        <div className="border-t border-line">
          <Pagination
            total={invites.length}
            page={page}
            pageSize={pageSize}
            pageSizes={PAGE_SIZES}
            onPageChange={setPage}
            onPageSizeChange={(size) => {
              setPageSize(size);
              setPage(1);
            }}
            noun={plural("members.invites.noun", invites.length)}
          />
        </div>
      )}

      <ConfirmDialog
        open={resending !== null}
        onOpenChange={(open) => !open && setResending(null)}
        title={t("members.invites.resendDialog.title", { email: resending?.email ?? "" })}
        description={t("members.invites.resendDialog.body", {
          workspace: workspace.name,
          role: resending ? t(`app.role.${resending.role}`) : "",
        })}
        confirmLabel={t("members.invites.resendDialog.confirm")}
        onConfirm={() => (resending ? resend(resending) : undefined)}
      >
        {resending && (
          <dl className="mb-2 flex flex-col gap-1.5 rounded-md bg-surface-sunk px-3.5 py-3 text-[14px]">
            <div className="flex flex-wrap justify-between gap-x-4">
              <dt className="text-ink-muted">{t("members.invites.resendDialog.currently")}</dt>
              <dd className="text-ink">{expiryText(resending.expires_at, now)}</dd>
            </div>
            <div className="flex flex-wrap justify-between gap-x-4">
              <dt className="text-ink-muted">{t("members.invites.resendDialog.after")}</dt>
              <dd className="font-semibold text-evergreen">
                {t("members.invites.expiresOn", {
                  date: formatDate(nextExpiry(new Date()), timeZone()),
                })}
              </dd>
            </div>
          </dl>
        )}
      </ConfirmDialog>

      <ConfirmDialog
        open={revoking !== null}
        onOpenChange={(open) => !open && setRevoking(null)}
        title={t("members.invites.revokeDialog.title", { email: revoking?.email ?? "" })}
        description={t("members.invites.revokeDialog.body", { workspace: workspace.name })}
        confirmLabel={t("members.invites.revokeDialog.confirm")}
        cancelLabel={t("members.invites.revokeDialog.keep")}
        destructive
        onConfirm={() => (revoking ? revoke(revoking) : undefined)}
      />
    </section>
  );
}

function InviteRow({
  invite,
  now,
  onShare,
  onResend,
  onRevoke,
}: {
  invite: Invite;
  now: Date;
  onShare: () => void;
  onResend: () => void;
  onRevoke: () => void;
}) {
  const soon = expiresSoon(invite.expires_at, now);
  return (
    <li className="flex flex-col gap-3 border-t border-line px-4 py-3.5 md:flex-row md:items-center md:gap-4 md:px-5">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <span
          aria-hidden="true"
          className="flex size-9 shrink-0 items-center justify-center rounded-pill border-[1.5px] border-dashed border-line-strong text-ink-muted"
        >
          <EnvelopeSimpleIcon className="size-4" />
        </span>
        <div className="flex min-w-0 flex-col">
          <span className="truncate text-[14px] font-semibold text-ink">{invite.email}</span>
          <span className="text-[13px] leading-[18px] text-ink-muted">
            {t("members.invites.invitedAs", {
              role: t(`app.role.${invite.role}`),
              sent: sentText(invite.sent_at, now),
            })}
          </span>
        </div>
      </div>
      <p className="flex flex-wrap items-center gap-x-2 pl-12 md:flex-col md:items-end md:gap-0.5 md:pl-0">
        <span className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-signal-watch">
          <span aria-hidden="true" className="size-1.5 rounded-pill bg-signal-watch" />
          {t("members.invites.pending")}
        </span>
        <span
          className={cn(
            "text-[13px] md:text-[12px]",
            soon ? "text-signal-watch" : "text-ink-muted",
          )}
        >
          {expiryText(invite.expires_at, now)}
        </span>
      </p>
      <div className="-ml-3 flex flex-wrap items-center gap-1 pl-12 md:ml-0 md:gap-2 md:pl-0">
        <Button
          variant="quiet"
          size="sm"
          aria-label={t("members.invites.shareFor", { email: invite.email })}
          onClick={onShare}
        >
          {t("members.invites.share")}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          aria-label={t("members.invites.resendFor", { email: invite.email })}
          onClick={onResend}
        >
          {t("members.invites.resend")}
        </Button>
        <Button
          variant="quiet"
          size="sm"
          destructive
          aria-label={t("members.invites.revokeFor", { email: invite.email })}
          onClick={onRevoke}
        >
          {t("members.invites.revoke")}
        </Button>
      </div>
    </li>
  );
}

function LoadingRows() {
  return (
    <div className="flex flex-col divide-y divide-line rounded-lg border border-line bg-surface-raised">
      {Array.from({ length: 3 }, (_, index) => (
        <div key={index} className="flex items-center gap-3 p-4">
          <Skeleton className="size-9 rounded-pill" />
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-4 w-48 max-w-full" />
            <Skeleton className="h-3.5 w-40" />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Invite a member (frame ManageMembers): email, role and departments. Once sent it shows the
 * code to share, since invite emails arrive with FND-010. Mounted per opening. */
export function InviteDialog({
  departments,
  onClose,
  onSent,
}: {
  departments: DepartmentOption[];
  onClose: () => void;
  onSent: () => void;
}) {
  const { workspace } = useShell();
  const toast = useToast();
  const refresh = useRefreshInvites();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("recruiter");
  const [departmentIds, setDepartmentIds] = useState<string[]>([]);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState<Invite | null>(null);
  const isAdmin = role === "admin";

  async function send(event?: FormEvent) {
    event?.preventDefault();
    const value = email.trim();
    if (!value) return setEmailError(t("members.invites.inviteDialog.emailRequired"));
    if (!isEmail(value)) return setEmailError(t("members.invites.inviteDialog.emailInvalid"));
    setEmailError(null);
    setBusy(true);
    try {
      const invite = unwrap(
        await api.POST("/v1/invites", {
          body: { email: value, role, department_ids: isAdmin ? [] : departmentIds },
        }),
      );
      await refresh();
      onSent();
      setSent(invite);
    } catch (failure) {
      const error = inviteFormError(failure);
      if (error.field) setEmailError(t(error.key, { workspace: workspace.name }));
      else toast({ title: t(error.key), tone: "error" });
    } finally {
      setBusy(false);
    }
  }

  function inviteAnother() {
    setSent(null);
    setEmail("");
    setEmailError(null);
  }

  if (sent) {
    return <ShareInviteDialog invite={sent} onClose={onClose} onInviteAnother={inviteAnother} />;
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => !open && onClose()}
      title={t("members.invites.inviteDialog.title")}
      description={t("members.invites.inviteDialog.body", { workspace: workspace.name })}
      size="md"
      dismissible={!busy}
      footer={
        <>
          <Button variant="secondary" disabled={busy} onClick={onClose}>
            {t("ui.cancel")}
          </Button>
          <Button type="submit" form="invite-form" loading={busy}>
            {t("members.invites.inviteDialog.send")}
          </Button>
        </>
      }
    >
      <form
        id="invite-form"
        noValidate
        className="flex flex-col gap-5 pb-2"
        onSubmit={(event) => void send(event)}
      >
        <Field
          label={t("members.invites.inviteDialog.email")}
          required
          error={emailError ?? undefined}
        >
          <Input
            type="email"
            autoComplete="off"
            inputMode="email"
            placeholder={t("members.invites.inviteDialog.emailPlaceholder")}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </Field>
        <Field
          label={t("members.invites.inviteDialog.role")}
          required
          hint={t(`members.invites.inviteDialog.roleHint.${role}`)}
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
      </form>
    </Dialog>
  );
}

/** The code and a ready-to-send message for an invite that was just sent or resent. */
export function ShareInviteDialog({
  invite,
  onClose,
  onInviteAnother,
}: {
  invite: Invite;
  onClose: () => void;
  onInviteAnother?: () => void;
}) {
  const { workspace } = useShell();
  const toast = useToast();
  const message = shareMessage(invite, workspace.name, env.siteUrl, timeZone());

  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      toast({ title: t("members.invites.shareDialog.copied") });
    } catch {
      toast({ title: t("members.invites.shareDialog.copyFailed"), tone: "error" });
    }
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => !open && onClose()}
      title={t("members.invites.shareDialog.title")}
      description={t("members.invites.shareDialog.body", { email: invite.email })}
      size="md"
      footer={
        <>
          {onInviteAnother && (
            <Button variant="secondary" onClick={onInviteAnother}>
              {t("members.invites.shareDialog.inviteAnother")}
            </Button>
          )}
          <Button onClick={onClose}>{t("members.invites.shareDialog.done")}</Button>
        </>
      }
    >
      <div className="flex flex-col gap-5 pb-2">
        <div className="flex flex-col gap-1.5">
          <p className="text-[14px] leading-5 font-semibold text-ink">
            {t("members.invites.shareDialog.code")}
          </p>
          <div className="flex items-center justify-between gap-3 rounded-md border border-line bg-surface-sunk px-4 py-3">
            <span
              data-testid="invite-code"
              className="font-mono text-[22px] leading-7 font-semibold tracking-[0.12em] text-ink"
            >
              {invite.code}
            </span>
            <Button variant="secondary" size="sm" onClick={() => void copy(invite.code)}>
              <CopyIcon aria-hidden="true" className="size-4" />
              {t("members.invites.shareDialog.copyCode")}
            </Button>
          </div>
        </div>
        <Field label={t("members.invites.shareDialog.message")}>
          <Textarea readOnly rows={4} value={message} className="resize-none" />
        </Field>
        <div>
          <Button variant="secondary" size="sm" onClick={() => void copy(message)}>
            <CopyIcon aria-hidden="true" className="size-4" />
            {t("members.invites.shareDialog.copyMessage")}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

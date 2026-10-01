"use client";

import {
  ArrowRightIcon,
  ClockCountdownIcon,
  EnvelopeSimpleIcon,
  LinkBreakIcon,
  WarningCircleIcon,
} from "@phosphor-icons/react";
import { ApiError } from "@fasthyr/api-client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { type ReactNode, useEffect, useState } from "react";

import { logOut } from "@/components/auth/log-out-button";
import { SignedInAs } from "@/components/auth/workspace-select-shell";
import { WorkspaceAvatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { type MessageKey, t } from "@/lib/i18n";
import { joinErrorKey } from "@/lib/workspaces/errors";
import { openWorkspace } from "@/lib/workspaces/activate";

type Preview = Awaited<ReturnType<typeof fetchPreview>>;

async function fetchPreview(inviteKey: string) {
  return unwrap(await api.GET("/v1/invites/{key}", { params: { path: { key: inviteKey } } }));
}

/** A code looks like AB12-CD34; anything else in the link is the token from the invite email. */
function acceptBody(inviteKey: string): { code: string } | { token: string } {
  return /^[A-Z0-9]{4}-[A-Z0-9]{4}$/i.test(inviteKey) ? { code: inviteKey } : { token: inviteKey };
}

/** Unknown links, and keys too long to be one, read as "not found". */
function isNotFound(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    (error.code === "invite_not_found" || error.code === "validation_failed")
  );
}

/**
 * Join a workspace from an invite link (S-04): the invite's workspace, inviter, role and
 * departments with one Join button, or why it can't be used. People already in the workspace
 * go straight to it.
 */
export function JoinInvite({
  inviteKey,
  email,
  returnPath,
}: {
  inviteKey: string;
  email: string;
  returnPath: string;
}) {
  const preview = useQuery({
    queryKey: keys.invitePreview(inviteKey),
    queryFn: () => fetchPreview(inviteKey),
    retry: false,
  });
  const logOutHere = () => void logOut(returnPath);

  return (
    <main className="page-gutter relative flex flex-1 flex-col items-center gap-6 pt-6 pb-12 md:pt-12 lg:justify-center lg:pt-0 lg:pb-18">
      <section className="flex w-full max-w-[560px] flex-col gap-6 rounded-lg border border-line bg-surface-raised p-6 shadow-raised md:p-10">
        {preview.isPending ? (
          <p role="status" className="type-body flex items-center gap-3 text-ink-muted">
            <Spinner />
            {t("join.loading")}
          </p>
        ) : preview.isError ? (
          isNotFound(preview.error) ? (
            <Problem
              icon={<LinkBreakIcon />}
              title="join.notFoundTitle"
              body={t("join.notFound")}
              action={<WorkspacesLink />}
            />
          ) : (
            <Problem
              icon={<WarningCircleIcon />}
              title="join.failedTitle"
              body={t("join.failed")}
              action={
                <Button variant="secondary" size="lg" onClick={() => void preview.refetch()}>
                  {t("join.retry")}
                </Button>
              }
            />
          )
        ) : (
          <InviteState preview={preview.data} inviteKey={inviteKey} onLogOut={logOutHere} />
        )}
      </section>

      <SignedInAs email={email} onLogOut={logOutHere} />
    </main>
  );
}

function InviteState({
  preview,
  inviteKey,
  onLogOut,
}: {
  preview: Preview;
  inviteKey: string;
  onLogOut: () => void;
}) {
  switch (preview.state) {
    case "ready":
      return <ReadyToJoin preview={preview} inviteKey={inviteKey} />;
    case "already_member":
      return <OpenExisting workspaceId={preview.workspace_id!} />;
    case "wrong_email":
      return (
        <Problem
          icon={<EnvelopeSimpleIcon />}
          title="join.wrongEmailTitle"
          body={t("join.wrongEmail", { email: preview.masked_email ?? "" })}
          action={
            <Button size="lg" className="w-full md:w-auto" onClick={onLogOut}>
              {t("auth.logOut")}
            </Button>
          }
        />
      );
    case "expired":
      return (
        <Problem
          icon={<ClockCountdownIcon />}
          title="join.expiredTitle"
          body={t("join.askAdmin")}
          action={<WorkspacesLink />}
        />
      );
    case "invalid":
      return (
        <Problem
          icon={<LinkBreakIcon />}
          title="join.invalidTitle"
          body={t("join.askAdmin")}
          action={<WorkspacesLink />}
        />
      );
  }
}

function ReadyToJoin({ preview, inviteKey }: { preview: Preview; inviteKey: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<MessageKey | null>(null);
  const workspace = preview.workspace_name ?? "";
  const role = preview.role ? t(`app.role.${preview.role}`) : "";

  async function join() {
    setError(null);
    setBusy(true);
    try {
      const joined = unwrap(await api.POST("/v1/invites/accept", { body: acceptBody(inviteKey) }));
      await openWorkspace(joined.id, "/");
    } catch (failure) {
      setError(joinErrorKey(failure));
      setBusy(false);
    }
  }

  return (
    <>
      <div className="flex flex-col items-start gap-4">
        <WorkspaceAvatar name={workspace} size="lg" />
        <div className="flex flex-col gap-2">
          <p className="type-label text-evergreen uppercase">{t("join.eyebrow")}</p>
          <h1 className="font-display text-[28px] leading-[34px] font-[560] tracking-[-0.02em] break-words md:text-[34px] md:leading-10">
            {workspace}
          </h1>
          <p className="type-body text-ink-muted">
            {preview.invited_by_name
              ? t("join.invitedBy", { inviter: preview.invited_by_name, workspace, role })
              : t("join.invited", { workspace, role })}
          </p>
        </div>
      </div>

      {preview.role === "admin" ? (
        <p className="type-body-sm text-ink-muted">{t("join.allDepartments")}</p>
      ) : (
        preview.departments.length > 0 && (
          <div className="flex flex-col gap-2">
            <h2 className="type-label text-ink-muted uppercase">{t("join.departments")}</h2>
            <ul className="flex flex-wrap gap-2">
              {preview.departments.map((name) => (
                <li key={name}>
                  <Badge tone="evergreen">{name}</Badge>
                </li>
              ))}
            </ul>
            <p className="type-body-sm text-ink-muted">{t("join.departmentsHint")}</p>
          </div>
        )
      )}

      <div className="flex flex-col gap-2">
        <Button size="lg" loading={busy} className="w-full" onClick={() => void join()}>
          <span className="truncate">{t("join.join", { workspace })}</span>
          <ArrowRightIcon aria-hidden="true" className="size-4 shrink-0" />
        </Button>
        {error && (
          <p role="alert" className="type-body-sm text-signal-gap">
            {t(error)}
          </p>
        )}
      </div>
    </>
  );
}

/** Already in the workspace (S-04): make it active and open it. */
function OpenExisting({ workspaceId }: { workspaceId: string }) {
  useEffect(() => {
    void openWorkspace(workspaceId, "/");
  }, [workspaceId]);
  return (
    <p role="status" className="type-body flex items-center gap-3 text-ink-muted">
      <Spinner />
      {t("join.openingYours")}
    </p>
  );
}

function Problem({
  icon,
  title,
  body,
  action,
}: {
  icon: ReactNode;
  title: MessageKey;
  body: string;
  action: ReactNode;
}) {
  return (
    <div className="flex flex-col items-start gap-5">
      <span
        aria-hidden="true"
        className="flex size-12 items-center justify-center rounded-md bg-persimmon-soft text-persimmon-ink [&>svg]:size-6"
      >
        {icon}
      </span>
      <div className="flex flex-col gap-2">
        <h1 className="text-[22px] leading-7 font-[650] md:text-[26px] md:leading-8">{t(title)}</h1>
        <p className="type-body text-ink-muted">{body}</p>
      </div>
      {action}
    </div>
  );
}

function WorkspacesLink() {
  return (
    <Link
      href="/workspaces"
      className="inline-flex min-h-11 items-center gap-2 font-semibold text-evergreen underline-offset-2 hover:underline"
    >
      {t("join.toWorkspaces")}
      <ArrowRightIcon aria-hidden="true" className="size-4" />
    </Link>
  );
}

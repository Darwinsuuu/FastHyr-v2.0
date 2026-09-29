"use client";

import {
  ArrowRightIcon,
  CaretDownIcon,
  PlusIcon,
  SignInIcon,
  SignOutIcon,
  UserCircleIcon,
} from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { type FormEvent, type ReactNode, useRef, useState } from "react";

import { TurnMark } from "@/components/brand/turn-mark";
import { logOut } from "@/components/auth/log-out-button";
import { ProfileDialog } from "@/components/auth/profile-dialog";
import { Avatar, WorkspaceAvatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Menu } from "@/components/ui/menu";
import { api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { cn } from "@/lib/cn";
import { env } from "@/lib/env";
import { type MessageKey, plural, t } from "@/lib/i18n";
import { activateWorkspace } from "@/lib/workspaces/activate";
import { createErrorKey, joinErrorKey, workspaceNameError } from "@/lib/workspaces/errors";

export interface ChooseWorkspaceUser {
  id: string;
  email: string;
  fullName: string;
  avatarUrl: string | null;
}

/** Makes the workspace active, then leaves for the app host (a full load, so no stale cache). */
async function openWorkspace(workspaceId: string, path: string) {
  await activateWorkspace(workspaceId);
  window.location.assign(new URL(path, env.appUrl).toString());
}

export function ChooseWorkspace({ user }: { user: ChooseWorkspaceUser }) {
  const firstName = user.fullName.split(" ")[0] ?? "";
  const displayName = user.fullName || user.email;
  const [profileOpen, setProfileOpen] = useState(false);
  const accountButton = useRef<HTMLButtonElement>(null);
  const workspaces = useQuery({
    queryKey: keys.myWorkspaces(),
    queryFn: async () => unwrap(await api.GET("/v1/me/workspaces")),
  });

  return (
    <div className="relative flex min-h-dvh flex-col overflow-hidden bg-surface">
      <svg
        viewBox="0 0 32 32"
        aria-hidden="true"
        className="pointer-events-none absolute -right-[140px] -bottom-[180px] hidden size-[520px] opacity-35 lg:block"
      >
        <ellipse cx="10" cy="13" rx="10" ry="13" className="fill-sage" />
        <ellipse cx="22" cy="19" rx="8" ry="10" className="fill-persimmon-soft" />
      </svg>

      <header className="page-gutter relative flex h-16 shrink-0 items-center justify-between gap-4 md:h-[72px]">
        <Link href="/" aria-label={t("auth.homeLink")} className="flex items-center gap-2.5">
          <TurnMark size={28} />
          <span className="font-display text-[20px] font-semibold tracking-[-0.02em]">
            {t("site.name")}
          </span>
        </Link>
        <Menu
          title={displayName}
          items={[
            {
              label: t("auth.profile.open"),
              icon: <UserCircleIcon aria-hidden="true" />,
              onSelect: () => setProfileOpen(true),
            },
            {
              label: t("auth.logOut"),
              icon: <SignOutIcon aria-hidden="true" />,
              destructive: true,
              onSelect: () => void logOut(),
            },
          ]}
          trigger={
            <button
              ref={accountButton}
              type="button"
              aria-label={t("workspaces.account")}
              className="flex min-h-11 items-center gap-2.5 rounded-pill border border-line bg-surface-raised py-1.5 pr-2.5 pl-1.5 text-ink hover:bg-surface-sunk data-[state=open]:bg-surface-sunk"
            >
              <Avatar id={user.id} name={displayName} src={user.avatarUrl} size="md" />
              <span className="hidden max-w-[200px] truncate text-[14px] font-semibold md:block">
                {displayName}
              </span>
              <CaretDownIcon aria-hidden="true" className="size-4 text-ink-muted" />
            </button>
          }
        />
      </header>

      <main className="page-gutter relative flex flex-1 flex-col items-center gap-8 pt-6 pb-12 md:gap-10 md:pt-10 lg:justify-center lg:pt-0 lg:pb-18">
        <div className="flex max-w-[640px] flex-col items-center gap-3 text-center">
          <p className="type-label text-evergreen uppercase">{t("workspaces.eyebrow")}</p>
          <h1 className="font-display text-[30px] leading-9 font-[560] tracking-[-0.02em] md:text-[36px] md:leading-[42px] lg:text-[44px] lg:leading-[50px]">
            {firstName ? t("workspaces.title", { name: firstName }) : t("workspaces.titleNoName")}
          </h1>
          <p className="type-body text-ink-muted">{t("workspaces.intro")}</p>
        </div>

        {workspaces.data && workspaces.data.length > 0 && (
          <section className="flex w-full max-w-[880px] flex-col gap-3">
            <h2 className="type-label text-ink-muted uppercase">{t("workspaces.yours")}</h2>
            <ul className="grid gap-3 md:grid-cols-2">
              {workspaces.data.map((workspace) => (
                <li key={workspace.id}>
                  <OpenWorkspaceButton
                    workspaceId={workspace.id}
                    name={workspace.name}
                    detail={`${t(`app.role.${workspace.role}`)} · ${plural("app.memberCount", workspace.member_count)}`}
                  />
                </li>
              ))}
            </ul>
          </section>
        )}

        <div className="grid w-full max-w-[880px] gap-4 md:grid-cols-2 md:gap-6">
          <CreateWorkspaceCard />
          <JoinWorkspaceCard email={user.email} />
        </div>

        <p className="text-center text-[14px] text-ink-muted">
          {t("workspaces.signedInAs")}{" "}
          <span className="font-semibold break-all text-ink">{user.email}</span> ·{" "}
          <button
            type="button"
            onClick={() => void logOut()}
            className="font-semibold text-evergreen underline-offset-2 hover:underline"
          >
            {t("workspaces.notYou")}
          </button>
        </p>
      </main>

      <ProfileDialog
        open={profileOpen}
        onOpenChange={setProfileOpen}
        user={{ id: user.id, name: displayName, avatarUrl: user.avatarUrl }}
        returnFocusTo={accountButton}
      />
    </div>
  );
}

function OpenWorkspaceButton({
  workspaceId,
  name,
  detail,
}: {
  workspaceId: string;
  name: string;
  detail: string;
}) {
  const [busy, setBusy] = useState(false);
  return (
    <button
      type="button"
      aria-label={t("workspaces.open", { name })}
      aria-busy={busy || undefined}
      disabled={busy}
      onClick={() => {
        setBusy(true);
        void openWorkspace(workspaceId, "/");
      }}
      className="flex min-h-18 w-full items-center gap-3 rounded-md border border-line bg-surface-raised p-4 text-left transition-colors hover:border-ink disabled:opacity-60"
    >
      <WorkspaceAvatar name={name} />
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="type-title truncate">{name}</span>
        <span className="type-body-sm text-ink-muted">{detail}</span>
      </span>
      <ArrowRightIcon aria-hidden="true" className="size-5 shrink-0 text-ink-muted" />
    </button>
  );
}

function ChoiceCard({
  icon,
  tone,
  title,
  body,
  raised,
  onSubmit,
  children,
}: {
  icon: ReactNode;
  tone: "evergreen" | "persimmon";
  title: string;
  body: string;
  raised?: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  children: ReactNode;
}) {
  return (
    <form
      noValidate
      onSubmit={onSubmit}
      className={cn(
        "flex flex-col gap-5 rounded-lg border border-line bg-surface-raised p-6 md:p-8",
        raised && "shadow-raised",
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          "flex size-12 items-center justify-center rounded-md [&>svg]:size-6",
          tone === "evergreen"
            ? "bg-evergreen-soft text-evergreen"
            : "bg-persimmon-soft text-persimmon-ink",
        )}
      >
        {icon}
      </span>
      <div className="flex flex-col gap-1.5">
        <h2 className="text-[20px] leading-7 font-[650] md:text-[22px]">{title}</h2>
        <p className="text-[15px] leading-[22px] text-ink-muted">{body}</p>
      </div>
      {children}
    </form>
  );
}

function CreateWorkspaceCard() {
  const [name, setName] = useState("");
  const [error, setError] = useState<MessageKey | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const invalid = workspaceNameError(name);
    setError(invalid);
    if (invalid) return;
    setBusy(true);
    try {
      const workspace = unwrap(await api.POST("/v1/workspaces", { body: { name: name.trim() } }));
      await openWorkspace(workspace.id, "/getting-started");
    } catch (failure) {
      setError(createErrorKey(failure));
      setBusy(false);
    }
  }

  return (
    <ChoiceCard
      icon={<PlusIcon />}
      tone="evergreen"
      raised
      title={t("workspaces.createTitle")}
      body={t("workspaces.createBody")}
      onSubmit={(event) => void submit(event)}
    >
      <Field
        label={t("workspaces.name")}
        hint={t("workspaces.nameHint")}
        error={error ? t(error) : undefined}
      >
        <Input
          name="workspace-name"
          autoComplete="organization"
          placeholder={t("workspaces.namePlaceholder")}
          maxLength={200}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </Field>
      <Button type="submit" size="lg" loading={busy} className="mt-auto w-full">
        {t("workspaces.create")}
        <ArrowRightIcon aria-hidden="true" className="size-4" />
      </Button>
    </ChoiceCard>
  );
}

function JoinWorkspaceCard({ email }: { email: string }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<MessageKey | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!code.trim()) {
      setError("workspaces.codeRequired");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const workspace = unwrap(await api.POST("/v1/invites/accept", { body: { code } }));
      await openWorkspace(workspace.id, "/");
    } catch (failure) {
      setError(joinErrorKey(failure));
      setBusy(false);
    }
  }

  return (
    <ChoiceCard
      icon={<SignInIcon />}
      tone="persimmon"
      title={t("workspaces.joinTitle")}
      body={t("workspaces.joinBody")}
      onSubmit={(event) => void submit(event)}
    >
      <Field
        label={t("workspaces.code")}
        hint={t("workspaces.codeHint", { email })}
        error={error ? t(error) : undefined}
      >
        <Input
          name="invite-code"
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          placeholder={t("workspaces.codePlaceholder")}
          value={code}
          onChange={(event) => setCode(event.target.value)}
          className="font-mono md:text-[14px]"
        />
      </Field>
      <Button type="submit" variant="secondary" size="lg" loading={busy} className="mt-auto w-full">
        {t("workspaces.join")}
      </Button>
    </ChoiceCard>
  );
}

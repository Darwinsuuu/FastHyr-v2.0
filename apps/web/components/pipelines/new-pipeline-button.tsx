"use client";

import { PlusIcon } from "@phosphor-icons/react";
import Link from "next/link";

import { useShell } from "@/components/app-shell/shell-context";
import { t } from "@/lib/i18n";
import { can } from "@/lib/permissions";

/** Opens the New pipeline wizard; only for roles that can edit pipelines. */
export function NewPipelineButton() {
  const { workspace } = useShell();
  if (!can(workspace.role, "edit_pipelines")) return null;
  return (
    <Link
      href="/pipelines/new"
      className="inline-flex min-h-11 items-center gap-2 self-start rounded-md bg-evergreen px-5 text-[15px] leading-5 font-semibold text-on-evergreen hover:brightness-110"
    >
      <PlusIcon aria-hidden="true" className="size-5" />
      {t("pipelines.newPipeline")}
    </Link>
  );
}

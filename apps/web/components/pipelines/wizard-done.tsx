"use client";

import { CheckIcon, PencilSimpleIcon } from "@phosphor-icons/react";
import Link from "next/link";

import { ShareTiles } from "@/components/pipelines/share-tiles";
import { WizardNote } from "@/components/pipelines/wizard-note";
import { Button } from "@/components/ui/button";
import { formatDayLong } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { Pipeline } from "@/lib/pipelines/wizard";

/** After publishing (frame NewPipeline done state, FR-PIPE-06): share the link, then move on. */
export function WizardDone({
  pipeline,
  workspaceSlug,
  pipelinesPath,
  onCreateAnother,
}: {
  pipeline: Pipeline;
  workspaceSlug: string;
  pipelinesPath: string;
  onCreateAnother: () => void;
}) {
  const title = pipeline.title ?? t("pipelines.wizard.done.fallbackTitle");
  const opens = pipeline.opens_at ? formatDayLong(pipeline.opens_at) : "";
  const heading =
    pipeline.status === "scheduled"
      ? t("pipelines.wizard.done.scheduledTitle", { title, date: opens })
      : pipeline.status === "paused_no_credits"
        ? t("pipelines.wizard.done.pausedTitle", { title })
        : t("pipelines.wizard.done.liveTitle", { title });

  return (
    <section
      aria-labelledby="wizard-done-title"
      className="page-gutter mx-auto flex w-full max-w-[808px] flex-col gap-6 py-8 md:py-12 lg:px-10"
    >
      <div className="flex flex-col gap-3">
        <span
          aria-hidden="true"
          className="flex size-14 items-center justify-center rounded-md bg-evergreen-soft text-evergreen"
        >
          <CheckIcon weight="bold" className="size-7" />
        </span>
        <h1
          id="wizard-done-title"
          className="font-display text-[28px] leading-[34px] font-[560] tracking-[-0.015em] break-words md:text-[34px] md:leading-10"
        >
          {heading}
        </h1>
        {pipeline.status === "paused_no_credits" && (
          <p className="type-body text-signal-gap">{t("pipelines.wizard.done.pausedBody")}</p>
        )}
        <p className="type-body text-ink-muted">{t("pipelines.wizard.done.body")}</p>
        {pipeline.status === "scheduled" && (
          <WizardNote icon={<PencilSimpleIcon aria-hidden="true" />}>
            {t("pipelines.wizard.done.editableNote", { date: opens })}
          </WizardNote>
        )}
      </div>
      {pipeline.slug && (
        <ShareTiles workspaceSlug={workspaceSlug} pipelineSlug={pipeline.slug} className="pb-2" />
      )}
      <div className="flex flex-col gap-2.5 sm:flex-row">
        <Link
          href={pipelinesPath}
          className="inline-flex min-h-12 items-center justify-center rounded-md bg-evergreen px-[22px] text-[15px] font-semibold text-on-evergreen hover:brightness-110"
        >
          {t("pipelines.wizard.goToPipelines")}
        </Link>
        <Button variant="secondary" size="lg" onClick={onCreateAnother}>
          {t("pipelines.wizard.done.createAnother")}
        </Button>
      </div>
    </section>
  );
}

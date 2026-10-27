"use client";

import { CheckIcon, ClockIcon, ProhibitIcon } from "@phosphor-icons/react";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { type ReactNode, type RefObject, useCallback, useState } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { Checkbox } from "@/components/ui/checkbox";
import { ConfirmDialog } from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";
import { api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { t } from "@/lib/i18n";
import {
  type ActionResult,
  CONFIRMED_ACTIONS,
  dialogFacts,
  type Fact,
  failureMessage,
  type LifecycleAction,
  type PipelineSummary,
  pausePoints,
  startNowBody,
  successMessage,
  summaryTitle,
} from "@/lib/pipelines/actions";

export interface PipelineActionsOptions {
  /** The workspace's time zone, for dates and days left in the dialogs. */
  timeZone: string;
  /** After archiving, e.g. the details page goes back to the list. */
  onArchived?: () => void;
}

/** Pause, resume, close, cancel, archive, start now and duplicate a pipeline (PIPE-005,
 * FR-PIPE-07). `run(action, pipeline)` asks first where the frame does (and before Start now),
 * then calls the API, refreshes what changed and says what happened. Render `dialogs` once. */
export function usePipelineActions({ timeZone, onArchived }: PipelineActionsOptions) {
  const { workspace } = useShell();
  const router = useRouter();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [pending, setPending] = useState<{
    action: LifecycleAction;
    summary: PipelineSummary;
    returnFocusTo?: RefObject<HTMLElement | null>;
  } | null>(null);
  const [notify, setNotify] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Fixed while a dialog is open so its numbers don't shift.
  const [now, setNow] = useState(() => new Date());

  const refresh = useCallback(() => {
    // The list, every pipeline and its dashboard, the flow band, and free credits.
    for (const queryKey of [
      keys.pipelines(workspace.id),
      keys.creditSummary(workspace.id),
      ["ws", workspace.id, "analytics"],
    ]) {
      void queryClient.invalidateQueries({ queryKey });
    }
  }, [queryClient, workspace.id]);

  const call = useCallback(
    async (action: LifecycleAction, id: string): Promise<ActionResult & { id: string }> => {
      const path = { params: { path: { pipeline_id: id } } };
      switch (action) {
        case "startNow":
          return unwrap(await api.POST("/v1/pipelines/{pipeline_id}/start-now", path));
        case "pause":
          return unwrap(await api.POST("/v1/pipelines/{pipeline_id}/pause", path));
        case "resume":
          return unwrap(await api.POST("/v1/pipelines/{pipeline_id}/resume", path));
        case "close":
          return unwrap(
            await api.POST("/v1/pipelines/{pipeline_id}/close", { ...path, body: { notify } }),
          );
        case "cancel":
          return unwrap(await api.POST("/v1/pipelines/{pipeline_id}/cancel", path));
        case "archive":
          return unwrap(await api.POST("/v1/pipelines/{pipeline_id}/archive", path));
        case "duplicate":
          return unwrap(await api.POST("/v1/pipelines/{pipeline_id}/duplicate", path));
      }
    },
    [notify],
  );

  const perform = useCallback(
    async (action: LifecycleAction, summary: PipelineSummary) => {
      const result = await call(action, summary.id);
      refresh();
      toast({ title: successMessage(action, summary, result), tone: "success" });
      if (action === "duplicate") router.push(`/pipelines/${encodeURIComponent(result.id)}/edit`);
      if (action === "archive") onArchived?.();
    },
    [call, refresh, toast, router, onArchived],
  );

  /** Runs `action` on the pipeline, asking first when it needs to. `returnFocusTo` is the menu
   * button the action was picked from, where focus goes back when its dialog closes. */
  const run = useCallback(
    (
      action: LifecycleAction,
      summary: PipelineSummary,
      returnFocusTo?: RefObject<HTMLElement | null>,
    ) => {
      if (CONFIRMED_ACTIONS.includes(action)) {
        setError(null);
        setNotify(true);
        setNow(new Date());
        setPending({ action, summary, returnFocusTo });
        return;
      }
      perform(action, summary).catch((caught: unknown) => {
        refresh();
        toast({ title: failureMessage(caught), tone: "error" });
      });
    },
    [perform, refresh, toast],
  );

  const dialogs = pending ? (
    <ActionDialog
      action={pending.action}
      summary={pending.summary}
      now={now}
      timeZone={timeZone}
      notify={notify}
      onNotifyChange={setNotify}
      error={error}
      returnFocusTo={pending.returnFocusTo}
      onOpenChange={(open) => !open && setPending(null)}
      onConfirm={async () => {
        setError(null);
        try {
          await perform(pending.action, pending.summary);
        } catch (caught) {
          refresh();
          setError(failureMessage(caught));
          throw caught;
        }
      }}
    />
  ) : null;

  return { run, dialogs };
}

type ConfirmedAction = "startNow" | "pause" | "close" | "cancel" | "archive";

const DESTRUCTIVE: ConfirmedAction[] = ["close", "cancel"];

function ActionDialog({
  action,
  summary,
  now,
  timeZone,
  notify,
  onNotifyChange,
  error,
  returnFocusTo,
  onOpenChange,
  onConfirm,
}: {
  action: LifecycleAction;
  summary: PipelineSummary;
  now: Date;
  timeZone: string;
  notify: boolean;
  onNotifyChange: (notify: boolean) => void;
  error: string | null;
  returnFocusTo?: RefObject<HTMLElement | null>;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => Promise<void>;
}) {
  const confirmed = action as ConfirmedAction;
  const key = `pipelines.actions.${confirmed}` as const;
  const title = summaryTitle(summary);
  const facts = dialogFacts(action, summary, now, timeZone);
  return (
    <ConfirmDialog
      open
      onOpenChange={onOpenChange}
      title={t(`${key}.title`, { title })}
      description={confirmed === "startNow" ? startNowBody(summary, timeZone) : t(`${key}.body`)}
      confirmLabel={t(`${key}.confirm`)}
      cancelLabel={t(`${key}.keep`)}
      destructive={DESTRUCTIVE.includes(confirmed)}
      onConfirm={onConfirm}
      returnFocusTo={returnFocusTo}
    >
      <div className="flex flex-col gap-4">
        {confirmed === "pause" && <PausePoints summary={summary} now={now} timeZone={timeZone} />}
        {facts.length > 0 && <Facts facts={facts} />}
        {confirmed === "close" && (
          <Checkbox
            checked={notify}
            onCheckedChange={onNotifyChange}
            label={t("pipelines.actions.close.notify")}
            description={t("pipelines.actions.close.notifyHint")}
          />
        )}
        {error && (
          <p role="alert" className="text-[14px] text-signal-gap">
            {error}
          </p>
        )}
      </div>
    </ConfirmDialog>
  );
}

function Facts({ facts }: { facts: Fact[] }) {
  return (
    <dl className="flex flex-col gap-2.5 rounded-md bg-surface-sunk p-4 text-[14px]">
      {facts.map((fact) => (
        <div key={fact.label} className="flex items-baseline justify-between gap-4">
          <dt className="text-ink-muted">{fact.label}</dt>
          <dd className="text-right font-[650] text-ink tabular-nums">{fact.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function PausePoints({
  summary,
  now,
  timeZone,
}: {
  summary: PipelineSummary;
  now: Date;
  timeZone: string;
}) {
  const { countdown, carryOn } = pausePoints(summary, now, timeZone);
  const point = (icon: ReactNode, title: string, body: string) => (
    <li className="flex gap-2.5">
      {icon}
      <span>
        <strong className="font-[650] text-ink">{title}</strong>{" "}
        <span className="text-ink-muted">{body}</span>
      </span>
    </li>
  );
  const iconClass = "mt-0.5 size-[18px] shrink-0";
  return (
    <ul className="flex flex-col gap-3 rounded-md bg-surface-sunk p-4 text-[14px] leading-5">
      {point(
        <ClockIcon aria-hidden="true" className={`${iconClass} text-signal-watch`} />,
        t("pipelines.actions.pause.countdownTitle"),
        countdown,
      )}
      {point(
        <ProhibitIcon aria-hidden="true" className={`${iconClass} text-signal-gap`} />,
        t("pipelines.actions.pause.blockedTitle"),
        t("pipelines.actions.pause.blockedBody"),
      )}
      {point(
        <CheckIcon aria-hidden="true" className={`${iconClass} text-evergreen`} />,
        t("pipelines.actions.pause.carryOnTitle"),
        carryOn,
      )}
    </ul>
  );
}

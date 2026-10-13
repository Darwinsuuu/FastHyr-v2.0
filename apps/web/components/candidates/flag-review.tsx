"use client";

import { PlayIcon } from "@phosphor-icons/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Textarea } from "@/components/ui/input";
import { SegmentedControl } from "@/components/ui/segmented-control";
import { useToast } from "@/components/ui/toast";
import { ApiError, api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import {
  draftFor,
  type FlagResolution,
  type FlagReviewDraft,
  flagLabel,
  flagReviewBody,
  flagReviewErrors,
  flagSpan,
  NOTE_MAX,
  RESOLUTIONS,
} from "@/lib/candidates/flags";
import {
  type ApplicationProfile,
  clock,
  confidenceWord,
  type ProfileFlag,
} from "@/lib/candidates/profile";
import { t } from "@/lib/i18n";
import { longDate } from "@/lib/pipelines/detail";

/** A-04: each flag with its moment, and No concern / Concern confirmed with a note for members
 * who resolve reviews. Hiring managers read the outcome only. */
export function FlagReviewList({
  profile,
  flags,
  canResolve,
  onSeek,
}: {
  profile: ApplicationProfile;
  flags: ProfileFlag[];
  canResolve: boolean;
  onSeek: (ms: number) => void;
}) {
  return (
    <ul className="flex flex-col gap-3">
      {flags.map((flag) => (
        <FlagItem
          key={flag.id}
          profile={profile}
          flag={flag}
          canResolve={canResolve}
          onSeek={onSeek}
        />
      ))}
    </ul>
  );
}

function FlagItem({
  profile,
  flag,
  canResolve,
  onSeek,
}: {
  profile: ApplicationProfile;
  flag: ProfileFlag;
  canResolve: boolean;
  onSeek: (ms: number) => void;
}) {
  const [editing, setEditing] = useState(false);
  const titleId = useId();
  const open = flag.status === "open";
  return (
    <li
      aria-labelledby={titleId}
      className="flex flex-col gap-3 rounded-md border border-line p-3 md:p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-2">
        <div className="flex min-w-0 flex-col gap-0.5">
          <p id={titleId} className="text-[14px] font-[650] text-ink">
            {flagLabel(flag)}
          </p>
          <p className="text-[13px] text-ink-muted tabular-nums">
            {confidenceWord(flag.confidence)} · {flagSpan(flag)}
          </p>
        </div>
        <button
          type="button"
          onClick={() => onSeek(flag.start_ms)}
          className="inline-flex min-h-11 items-center gap-1.5 rounded-pill border border-line px-3 text-[13px] font-[650] text-ink tabular-nums hover:bg-surface md:min-h-8"
        >
          <PlayIcon aria-hidden="true" weight="fill" className="size-3" />
          {t("candidates.profile.flagReview.listen", { time: clock(flag.start_ms) })}
        </button>
      </div>
      {canResolve && (open || editing) ? (
        <ReviewForm
          profile={profile}
          flag={flag}
          onDone={() => setEditing(false)}
          onCancel={open ? undefined : () => setEditing(false)}
        />
      ) : open ? (
        <p className="text-[13px] text-ink-muted">{t("candidates.profile.flagReview.waiting")}</p>
      ) : (
        <Outcome
          profile={profile}
          flag={flag}
          onChange={canResolve ? () => setEditing(true) : undefined}
        />
      )}
    </li>
  );
}

function Outcome({
  profile,
  flag,
  onChange,
}: {
  profile: ApplicationProfile;
  flag: ProfileFlag;
  onChange?: () => void;
}) {
  if (flag.status === "open") return null;
  const outcome = t(`candidates.profile.flagReview.outcomes.${flag.status}`);
  const date = flag.resolved_at ? longDate(new Date(flag.resolved_at), profile.timezone) : "";
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={flag.status === "concern_confirmed" ? "gap" : "strong"}>{outcome}</Badge>
        <span className="text-[13px] text-ink-muted">
          {flag.resolved_by
            ? t("candidates.profile.flagReview.reviewedBy", { name: flag.resolved_by, date })
            : t("candidates.profile.flagReview.reviewedOn", { date })}
        </span>
      </div>
      {flag.note && (
        <p className="rounded-md bg-surface p-3 text-[13px] leading-[19px] break-words whitespace-pre-line text-ink">
          {flag.note}
        </p>
      )}
      {onChange && (
        <Button variant="quiet" size="sm" className="-ml-3.5 self-start" onClick={onChange}>
          {t("candidates.profile.flagReview.change")}
        </Button>
      )}
    </div>
  );
}

function ReviewForm({
  profile,
  flag,
  onDone,
  onCancel,
}: {
  profile: ApplicationProfile;
  flag: ProfileFlag;
  onDone: () => void;
  onCancel?: () => void;
}) {
  const { workspace } = useShell();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [draft, setDraft] = useState<FlagReviewDraft>(() => draftFor(flag));
  const [submitted, setSubmitted] = useState(false);
  const errors = submitted ? flagReviewErrors(draft) : {};

  const save = useMutation({
    mutationFn: async (body: ReturnType<typeof flagReviewBody>) =>
      unwrap(
        await api.PATCH("/v1/integrity-flags/{flag_id}", {
          params: { path: { flag_id: flag.id } },
          body,
        }),
      ),
    onSuccess: (result) => {
      const allReviewed = profile.open_flags > 0 && result.application.open_flags === 0;
      toast({
        title: t("candidates.profile.flagReview.saved"),
        description: allReviewed ? t("candidates.profile.flagReview.allReviewed") : undefined,
        tone: "success",
      });
      onDone();
      void queryClient.invalidateQueries({ queryKey: keys.application(workspace.id, profile.id) });
      // The Candidates tab's Flagged filter and counts follow the overlay.
      void queryClient.invalidateQueries({
        queryKey: ["ws", workspace.id, "pipelines", profile.pipeline.id],
      });
    },
  });

  function submit() {
    setSubmitted(true);
    const found = flagReviewErrors(draft);
    if (found.status || found.note || !draft.status) return;
    save.mutate(flagReviewBody({ ...draft, status: draft.status }));
  }

  const failure =
    save.error instanceof ApiError && save.error.status === 404
      ? t("candidates.profile.flagReview.gone")
      : save.error
        ? t("candidates.profile.flagReview.failed")
        : null;

  return (
    <form
      noValidate
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <div className="flex flex-col gap-1.5">
        <SegmentedControl<FlagResolution | "">
          label={t("candidates.profile.flagReview.decision")}
          options={RESOLUTIONS.map((value) => ({
            value,
            label: t(`candidates.profile.flagReview.outcomes.${value}`),
          }))}
          value={draft.status ?? ""}
          onValueChange={(value) => setDraft({ ...draft, status: value || null })}
          className="self-start"
        />
        {errors.status && (
          <p role="alert" className="text-[13px] leading-[18px] font-semibold text-signal-gap">
            {errors.status}
          </p>
        )}
      </div>
      <Field
        label={t("candidates.profile.flagReview.noteLabel")}
        hint={t("candidates.profile.flagReview.noteHint")}
        error={errors.note}
        required={draft.status === "concern_confirmed"}
      >
        <Textarea
          rows={3}
          maxLength={NOTE_MAX}
          value={draft.note}
          onChange={(event) => setDraft({ ...draft, note: event.target.value })}
        />
      </Field>
      {failure && (
        <p role="alert" className="text-[13px] leading-[18px] font-semibold text-signal-gap">
          {failure}
        </p>
      )}
      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        {onCancel && (
          <Button type="button" variant="secondary" onClick={onCancel}>
            {t("candidates.profile.flagReview.cancel")}
          </Button>
        )}
        <Button type="submit" loading={save.isPending}>
          {t("candidates.profile.flagReview.save")}
        </Button>
      </div>
    </form>
  );
}

"use client";

import { UserFocusIcon } from "@phosphor-icons/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Textarea } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { api, unwrap } from "@/lib/api/client";
import type { ApplicationProfile } from "@/lib/candidates/profile";
import {
  outcomeKey,
  type ProfileReviewRequest,
  RESOLUTION_NOTE_MAX,
  resolutionBody,
  resolutionError,
  resolutionFailure,
  type ReviewOutcome,
  reviewOutcomes,
} from "@/lib/candidates/review-requests";
import { t } from "@/lib/i18n";
import { longDate } from "@/lib/pipelines/detail";

/**
 * A-03 (ADR-015): "{name} asked for a person to review this decision on {date}." with the
 * candidate's message, then "Uphold decision" and, for an automated decision, "Invite to
 * interview" (résumé) or "Move to Ready for review" (interview). Both ask for a note only the
 * team sees. Hiring managers read it only.
 */
export function ReviewRequestBanner({
  profile,
  request,
  canResolve,
}: {
  profile: ApplicationProfile;
  request: ProfileReviewRequest;
  canResolve: boolean;
}) {
  const [outcome, setOutcome] = useState<ReviewOutcome | null>(null);
  const name = profile.candidate.name;
  const date = longDate(new Date(request.created_at), profile.timezone);
  return (
    <section
      aria-labelledby="review-request-title"
      className="flex flex-col gap-4 rounded-lg border border-signal-watch bg-surface-raised p-4 md:flex-row md:items-start md:gap-5 md:p-5"
    >
      <span
        aria-hidden="true"
        className="flex size-10 shrink-0 items-center justify-center rounded-md bg-surface-sunk text-ink [&_svg]:size-5"
      >
        <UserFocusIcon />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        <div className="flex flex-col gap-1">
          <h2 id="review-request-title" className="type-title break-words">
            {t("candidates.reviewRequest.title", { name, date })}
          </h2>
          <p className="text-[14px] leading-5 text-ink-muted">
            {t(`candidates.reviewRequest.decision.${request.decision_type}`)}{" "}
            {request.by_person && t("candidates.reviewRequest.byPerson")}
          </p>
        </div>
        {request.message ? (
          <blockquote className="border-l-2 border-signal-watch pl-3 text-[15px] leading-[22px] break-words whitespace-pre-line text-ink">
            {request.message}
          </blockquote>
        ) : (
          <p className="text-[14px] text-ink-muted italic">
            {t("candidates.reviewRequest.noMessage")}
          </p>
        )}
        {canResolve && (
          <div className="flex flex-col gap-2.5 sm:flex-row sm:flex-wrap">
            {reviewOutcomes(request).map((value) => (
              <Button
                key={value}
                variant={value === "uphold" ? "secondary" : "primary"}
                className="w-full sm:w-auto"
                onClick={() => setOutcome(value)}
              >
                {t(`candidates.reviewRequest.${outcomeKey(request, value)}.button`)}
              </Button>
            ))}
          </div>
        )}
      </div>
      <ResolveDialog
        profile={profile}
        request={request}
        outcome={outcome}
        onClose={() => setOutcome(null)}
      />
    </section>
  );
}

function ResolveDialog({
  profile,
  request,
  outcome,
  onClose,
}: {
  profile: ApplicationProfile;
  request: ProfileReviewRequest;
  /** Null closes the dialog. */
  outcome: ReviewOutcome | null;
  onClose: () => void;
}) {
  const { workspace } = useShell();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [note, setNote] = useState("");
  const [submitted, setSubmitted] = useState(false);
  // The last outcome stays while the dialog closes.
  const [shown, setShown] = useState<ReviewOutcome>("uphold");
  if (outcome !== null && outcome !== shown) setShown(outcome);
  const key = outcomeKey(request, shown);
  const name = profile.candidate.name;

  const save = useMutation({
    mutationFn: async () =>
      unwrap(
        await api.POST("/v1/review-requests/{request_id}/resolve", {
          params: { path: { request_id: request.id } },
          body: resolutionBody(shown, note),
        }),
      ),
    onSuccess: (result) => {
      toast({
        title: t(`candidates.reviewRequest.${key}.done`, { name }),
        description: result.emailed ? t("candidates.decisions.emailed") : undefined,
        tone: "success",
      });
      close();
      // The stage and the overlay show on the profile, the Candidates tab and the dashboards.
      void queryClient.invalidateQueries({ queryKey: ["ws", workspace.id] });
    },
  });

  function close() {
    setNote("");
    setSubmitted(false);
    save.reset();
    onClose();
  }

  const error = submitted ? resolutionError(note) : null;
  return (
    <Dialog
      open={outcome !== null}
      onOpenChange={(open) => !open && close()}
      title={t(`candidates.reviewRequest.${key}.title`, { name })}
      description={t(`candidates.reviewRequest.${key}.body`)}
      size="md"
      dismissible={!save.isPending}
      footer={
        <>
          <Button variant="secondary" disabled={save.isPending} onClick={close}>
            {t("ui.cancel")}
          </Button>
          <Button type="submit" form="review-resolve-form" loading={save.isPending}>
            {t(`candidates.reviewRequest.${key}.confirm`)}
          </Button>
        </>
      }
    >
      <form
        id="review-resolve-form"
        noValidate
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          setSubmitted(true);
          if (resolutionError(note)) return;
          save.mutate();
        }}
      >
        <Field
          label={t("candidates.reviewRequest.noteLabel")}
          hint={t("candidates.reviewRequest.noteHint")}
          error={error ?? undefined}
          required
        >
          <Textarea
            rows={4}
            maxLength={RESOLUTION_NOTE_MAX}
            placeholder={t(`candidates.reviewRequest.${key}.placeholder`)}
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
        </Field>
        {save.error && (
          <p role="alert" className="text-[14px] leading-5 font-semibold text-signal-gap">
            {resolutionFailure(save.error)}
          </p>
        )}
      </form>
    </Dialog>
  );
}

"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type RefObject, useState } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Textarea } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { api, unwrap } from "@/lib/api/client";
import {
  advanceBody,
  type Decision,
  type DecisionDraft,
  decisionError,
  decisionFailure,
  EMPTY_DRAFT,
  NOTE_MAX,
  REASON_MAX,
  rejectBody,
} from "@/lib/candidates/decisions";
import { t } from "@/lib/i18n";

export interface DecisionTarget {
  /** The application's ID. */
  id: string;
  name: string;
}

/**
 * "Advance to next round" (SCREEN_SPECS.md A-02) and "Reject candidate" (frame PipelineView):
 * a note or a required reason for the team, and whether to email the candidate. On success the
 * profile, the Candidates tab and the dashboards re-read. Shared by the Candidates tab's row menu
 * and the candidate profile.
 */
export function DecisionDialog({
  decision,
  target,
  onOpenChange,
  returnFocusTo,
}: {
  decision: Decision;
  /** The candidate; null closes the dialog. */
  target: DecisionTarget | null;
  onOpenChange: (open: boolean) => void;
  returnFocusTo?: RefObject<HTMLElement | null>;
}) {
  const { workspace } = useShell();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [draft, setDraft] = useState<DecisionDraft>(EMPTY_DRAFT);
  const [submitted, setSubmitted] = useState(false);
  const open = target !== null;

  const save = useMutation({
    mutationFn: async ({ id, draft }: { id: string; draft: DecisionDraft }) => {
      const path = { params: { path: { application_id: id } } };
      return decision === "advance"
        ? unwrap(
            await api.POST("/v1/applications/{application_id}/advance", {
              ...path,
              body: advanceBody(draft),
            }),
          )
        : unwrap(
            await api.POST("/v1/applications/{application_id}/reject", {
              ...path,
              body: rejectBody(draft),
            }),
          );
    },
    onSuccess: (result) => {
      toast({
        title: t(`candidates.decisions.${decision}.done`, { name: target?.name ?? "" }),
        description: result.emailed ? t("candidates.decisions.emailed") : undefined,
        tone: "success",
      });
      setOpen(false);
      // The stage shows on the profile, the Candidates tab, the pipeline and the dashboards.
      void queryClient.invalidateQueries({ queryKey: ["ws", workspace.id] });
    },
  });

  // Each opening starts from a clean form.
  function setOpen(next: boolean) {
    if (!next) {
      setDraft(EMPTY_DRAFT);
      setSubmitted(false);
      save.reset();
    }
    onOpenChange(next);
  }

  const error = submitted ? decisionError(decision, draft) : null;
  const failure = save.error ? decisionFailure(save.error) : null;

  function submit() {
    setSubmitted(true);
    if (!target || decisionError(decision, draft)) return;
    save.mutate({ id: target.id, draft });
  }

  const name = target?.name ?? "";
  return (
    <Dialog
      open={open}
      onOpenChange={setOpen}
      title={t(`candidates.decisions.${decision}.title`, { name })}
      description={t(`candidates.decisions.${decision}.body`)}
      size="md"
      dismissible={!save.isPending}
      returnFocusTo={returnFocusTo}
      footer={
        <>
          <Button variant="secondary" disabled={save.isPending} onClick={() => setOpen(false)}>
            {t("ui.cancel")}
          </Button>
          <Button
            type="submit"
            form="decision-form"
            destructive={decision === "reject"}
            loading={save.isPending}
          >
            {t(`candidates.decisions.${decision}.confirm`)}
          </Button>
        </>
      }
    >
      <form
        id="decision-form"
        noValidate
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <Field
          label={t(`candidates.decisions.${decision}.textLabel`)}
          hint={t(`candidates.decisions.${decision}.textHint`)}
          error={error ?? undefined}
          required={decision === "reject"}
        >
          <Textarea
            rows={4}
            maxLength={decision === "reject" ? REASON_MAX : NOTE_MAX}
            placeholder={t(`candidates.decisions.${decision}.placeholder`)}
            value={draft.text}
            onChange={(event) => setDraft({ ...draft, text: event.target.value })}
          />
        </Field>
        <Checkbox
          label={t(`candidates.decisions.${decision}.email`)}
          description={t(`candidates.decisions.${decision}.emailHint`)}
          checked={draft.email}
          onCheckedChange={(email) => setDraft({ ...draft, email })}
        />
        {failure && (
          <p role="alert" className="text-[14px] leading-5 font-semibold text-signal-gap">
            {failure}
          </p>
        )}
      </form>
    </Dialog>
  );
}

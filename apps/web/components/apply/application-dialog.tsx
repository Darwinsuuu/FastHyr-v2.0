"use client";

import { CheckIcon } from "@phosphor-icons/react";
import { type FormEvent, useState } from "react";

import { ConsentCheckbox } from "@/components/consent/consent-checkbox";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { FileDrop } from "@/components/ui/file-drop";
import { Input } from "@/components/ui/input";
import { PhoneInput } from "@/components/ui/phone-input";
import { api, unwrap } from "@/lib/api/client";
import { type PublicPipeline, type SourceTag } from "@/lib/apply";
import {
  type ApplicationForm,
  emptyForm,
  type FormErrors,
  formErrors,
  RESUME_MAX_BYTES,
  RESUME_TYPES,
  type SubmitProblem,
  type SubmittedApplication,
  submitProblem,
  submitRequest,
} from "@/lib/apply/form";
import type { Candidate } from "@/lib/apply/session";
import { t } from "@/lib/i18n";
import type { Notice } from "@/lib/notices";

const FORM_ID = "application-form";

/**
 * The application form (frame Apply, FR-APPLY-03): the account it goes under, the résumé, contact
 * details and the versioned apply consent. Sending uploads the résumé to a signed URL, then
 * submits it, which uses 1 credit (APPLY-003).
 */
export function ApplicationDialog({
  open,
  onOpenChange,
  pipeline,
  candidate,
  notice,
  source,
  onNotYou,
  onApplied,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  pipeline: PublicPipeline;
  candidate: Candidate;
  /** The current apply notice (COMP-002); null if it couldn't be loaded. */
  notice: Notice | null;
  /** The source tag to record (`applySource()`). */
  source: () => SourceTag;
  /** Signs out and asks for the right account. */
  onNotYou: () => void;
  onApplied: (application: SubmittedApplication, fullName: string) => void;
}) {
  const [form, setForm] = useState(() => emptyForm(candidate.name, candidate.email));
  const [tried, setTried] = useState(false);
  const [sending, setSending] = useState(false);
  const [problem, setProblem] = useState<SubmitProblem | null>(null);

  const errors: FormErrors = tried ? formErrors(form) : {};
  const fieldError = (field: keyof FormErrors) => {
    if (problem?.field === field) return t(problem.message);
    const key = errors[field];
    return key ? t(key) : undefined;
  };
  const update = (changes: Partial<ApplicationForm>) => {
    setForm((current) => ({ ...current, ...changes }));
    // A new file or new details may fix what the server said; the footer explains anything else.
    if (problem?.field && problem.field in changes) setProblem(null);
  };
  const footNote = problem
    ? problem.field
      ? t("apply.form.attention")
      : t(problem.message)
    : tried && Object.keys(errors).length > 0
      ? t("apply.form.attention")
      : t("apply.form.required");

  async function send(event: FormEvent) {
    event.preventDefault();
    if (sending || !notice) return;
    setTried(true);
    setProblem(null);
    if (Object.keys(formErrors(form)).length > 0 || !form.resume) return;
    setSending(true);
    try {
      const target = unwrap(
        await api.POST("/v1/candidate/pipelines/{pipeline_id}/resume-upload", {
          params: { path: { pipeline_id: pipeline.id } },
        }),
      );
      const uploaded = await fetch(target.url, {
        method: "PUT",
        body: form.resume,
        headers: { "Content-Type": "application/pdf" },
      });
      if (!uploaded.ok) {
        setProblem({ field: "resume", message: "apply.form.errors.uploadFailed" });
        return;
      }
      const application = unwrap(
        await api.POST("/v1/candidate/applications", {
          body: submitRequest(form, {
            pipelineId: pipeline.id,
            uploadId: target.upload_id,
            noticeId: notice.id,
            source: source(),
          }),
        }),
      );
      onApplied(application, form.fullName);
    } catch (failure) {
      setProblem(submitProblem(failure));
    } finally {
      setSending(false);
    }
  }

  const provider = t(`auth.provider.${candidate.provider}`);

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      size="lg"
      dismissible={!sending}
      title={
        <span className="flex flex-col gap-1">
          <span className="text-[13px] leading-5 font-normal tracking-normal text-ink-muted">
            {t("apply.form.applyingTo", { company: pipeline.company.name })}
          </span>
          <span className="font-display text-[24px] leading-[30px] font-[560] md:text-[26px] md:leading-8">
            {pipeline.title}
          </span>
        </span>
      }
      footer={
        <div className="flex w-full flex-col gap-3 md:flex-row md:items-center md:justify-between md:gap-4">
          <p
            aria-live="polite"
            className={
              problem && !problem.field
                ? "text-[13px] leading-5 font-semibold text-signal-gap"
                : "text-[13px] leading-5 text-ink-muted"
            }
          >
            {footNote}
          </p>
          <div className="flex gap-2.5 max-md:*:flex-1">
            <Button variant="secondary" disabled={sending} onClick={() => onOpenChange(false)}>
              {t("ui.cancel")}
            </Button>
            <Button
              side="candidate"
              type="submit"
              form={FORM_ID}
              loading={sending}
              disabled={!notice || problem?.closed}
            >
              {t("apply.form.send")}
            </Button>
          </div>
        </div>
      }
    >
      <form id={FORM_ID} noValidate onSubmit={send} className="flex flex-col gap-5">
        <div className="flex items-center gap-3 rounded-md bg-surface px-3.5 py-3">
          <Avatar id={candidate.id} name={candidate.name} />
          <span className="flex min-w-0 flex-1 flex-col">
            <span className="truncate text-[14px] leading-5 font-semibold">{candidate.email}</span>
            <span className="text-[12px] leading-4 text-ink-muted">
              {t("apply.form.signedInAs", { provider })}
            </span>
          </span>
          <button
            type="button"
            onClick={onNotYou}
            disabled={sending}
            className="min-h-11 shrink-0 px-1 text-[13px] font-semibold text-persimmon-ink hover:underline md:min-h-0"
          >
            {t("apply.form.notYou")}
          </button>
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-[14px] leading-5 font-semibold text-ink">
            {t("apply.form.resume")} <span className="text-signal-gap">*</span>
          </span>
          <FileDrop
            accept={RESUME_TYPES}
            maxSize={RESUME_MAX_BYTES}
            file={form.resume}
            onFileChange={(resume) => update({ resume })}
            label={t("apply.form.resumeDrop")}
            hint={t("apply.form.resumeHint")}
            error={fieldError("resume")}
            disabled={sending}
          />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <Field
            label={<Required>{t("apply.form.fullName")}</Required>}
            error={fieldError("fullName")}
            required
            className="md:col-span-2"
          >
            <Input
              autoComplete="name"
              maxLength={120}
              value={form.fullName}
              disabled={sending}
              onChange={(event) => update({ fullName: event.target.value })}
            />
          </Field>
          <div className="flex flex-col gap-1.5 md:col-span-2">
            <span className="text-[14px] leading-5 font-semibold text-ink">
              {t("apply.form.email")}
            </span>
            <p className="flex min-h-12 flex-wrap items-center justify-between gap-x-3 gap-y-1 rounded-sm border border-line bg-surface px-3.5 py-2 text-[15px] text-ink/85">
              <span className="min-w-0 break-all">{candidate.email}</span>
              <span className="inline-flex items-center gap-1 text-[12px] font-semibold text-evergreen">
                <CheckIcon aria-hidden="true" weight="bold" className="size-3.5" />
                {t("apply.form.verifiedBy", { provider })}
              </span>
            </p>
          </div>
          <Field
            label={<Required>{t("apply.form.phone")}</Required>}
            error={fieldError("phone")}
            required
            className="md:col-span-2"
          >
            <PhoneInput
              value={form.phone}
              disabled={sending}
              onValueChange={(phone) => update({ phone })}
            />
          </Field>
          <Field label={<Optional>{t("apply.form.city")}</Optional>}>
            <Input
              autoComplete="address-level2"
              maxLength={100}
              placeholder={t("apply.form.cityPlaceholder")}
              value={form.city}
              disabled={sending}
              onChange={(event) => update({ city: event.target.value })}
            />
          </Field>
          <Field
            label={<Optional>{t("apply.form.profileUrl")}</Optional>}
            error={fieldError("profileUrl")}
          >
            <Input
              type="url"
              inputMode="url"
              autoComplete="url"
              maxLength={500}
              placeholder="https://"
              value={form.profileUrl}
              disabled={sending}
              onChange={(event) => update({ profileUrl: event.target.value })}
            />
          </Field>
        </div>

        {notice ? (
          <ConsentCheckbox
            notice={notice}
            values={{
              company: pipeline.company.name,
              choices: { interview: pipeline.interview_format ?? "video_voice" },
            }}
            checked={form.consent}
            onCheckedChange={(consent) => update({ consent })}
            error={fieldError("consent")}
          />
        ) : (
          <p role="alert" className="text-[14px] leading-5 font-semibold text-signal-gap">
            {t("apply.form.errors.noticeMissing")}
          </p>
        )}
      </form>
    </Dialog>
  );
}

function Required({ children }: { children: string }) {
  return (
    <>
      {children} <span className="text-signal-gap">*</span>
    </>
  );
}

function Optional({ children }: { children: string }) {
  return (
    <>
      {children} <span className="font-medium text-ink-muted">{t("apply.form.optional")}</span>
    </>
  );
}

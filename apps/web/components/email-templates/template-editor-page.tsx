"use client";

import { ApiError } from "@fasthyr/api-client";
import {
  ArrowCounterClockwiseIcon,
  CheckCircleIcon,
  ClockIcon,
  LockSimpleIcon,
  PaperPlaneTiltIcon,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { cn } from "@/lib/cn";
import {
  apiProblems,
  CATEGORY,
  changeOf,
  type EmailTemplate,
  type EmailTemplateVersion,
  type FieldProblem,
  hasReviewLink,
  insertable,
  problems as findProblems,
  REVIEW_LINK,
  SAMPLE,
  sampleSubject,
  type TemplateKey,
} from "@/lib/email-templates";
import { formatDate, formatDateTime } from "@/lib/format";
import { t } from "@/lib/i18n";

import { browserTimeZone, CATEGORY_TONE } from "./email-templates-page";
import { RichTextEditor, type RichTextEditorHandle } from "./rich-text-editor";

interface Draft {
  subject: string;
  body: string;
}

/** Edit email template (frame EditEmailTemplate + A-07, FR-MSG-02): subject and message with
 * parameter chips, reset to default, change history with view and restore, and a test email
 * to yourself. Admins and Recruiters. */
export function TemplateEditorPage({ templateKey }: { templateKey: TemplateKey }) {
  const { workspace } = useShell();
  const templateQueryKey = keys.emailTemplate(workspace.id, templateKey);
  const versionsQueryKey = keys.emailTemplateVersions(workspace.id, templateKey);

  const template = useQuery({
    queryKey: templateQueryKey,
    queryFn: async () =>
      unwrap(
        await api.GET("/v1/email-templates/{key}", { params: { path: { key: templateKey } } }),
      ),
    // A draft is being edited: don't swap the content underneath it on refocus.
    refetchOnWindowFocus: false,
  });
  const versions = useQuery({
    queryKey: versionsQueryKey,
    queryFn: async () =>
      unwrap(
        await api.GET("/v1/email-templates/{key}/versions", {
          params: { path: { key: templateKey } },
        }),
      ),
  });

  if (template.isError) {
    const missing = template.error instanceof ApiError && template.error.status === 404;
    return (
      <div className="page-gutter py-10">
        <div className="rounded-lg border border-line bg-surface-raised">
          <EmptyState
            title={missing ? t("emailTemplates.editor.notFound") : t("emailTemplates.loadFailed")}
            action={
              <Link href="/settings/email-templates" className="font-semibold text-evergreen">
                {t("emailTemplates.editor.backToList")}
              </Link>
            }
          />
        </div>
      </div>
    );
  }
  if (!template.data) return <LoadingEditor />;
  return (
    <Editor
      templateKey={templateKey}
      loaded={template.data}
      versions={versions.data?.versions ?? []}
      versionsLoading={versions.isPending}
    />
  );
}

function Editor({
  templateKey,
  loaded,
  versions,
  versionsLoading,
}: {
  templateKey: TemplateKey;
  loaded: EmailTemplate;
  versions: EmailTemplateVersion[];
  versionsLoading: boolean;
}) {
  const { workspace, user } = useShell();
  const router = useRouter();
  const toast = useToast();
  const queryClient = useQueryClient();
  const templateQueryKey = keys.emailTemplate(workspace.id, templateKey);
  const versionsQueryKey = keys.emailTemplateVersions(workspace.id, templateKey);

  const [draft, setDraft] = useState<Draft>({ subject: loaded.subject, body: loaded.body_html });
  const [dirty, setDirty] = useState(false);
  // Bumped whenever the editor should show other content (reset, restored, a version).
  const [contentKey, setContentKey] = useState(0);
  const [viewing, setViewing] = useState<EmailTemplateVersion | null>(null);
  const [serverProblems, setServerProblems] = useState<FieldProblem[]>([]);
  const [showProblems, setShowProblems] = useState(false);
  const [saving, setSaving] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [testOpen, setTestOpen] = useState(false);
  // A new test dialog each time it opens, so it starts at "ready".
  const [testRun, setTestRun] = useState(0);
  const editorRef = useRef<RichTextEditorHandle>(null);
  const messageLabelId = useId();
  const messageErrorId = useId();

  function load(next: EmailTemplate) {
    setDraft({ subject: next.subject, body: next.body_html });
    setDirty(false);
    setViewing(null);
    setServerProblems([]);
    setShowProblems(false);
    setContentKey((value) => value + 1);
  }

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const name = t(`emailTemplates.templates.${templateKey}.name`);
  const category = CATEGORY[templateKey];
  const timing = t(`emailTemplates.templates.${templateKey}.timing`);
  const shown: Draft = viewing ? { subject: viewing.subject, body: viewing.body_html } : draft;
  const allowed = loaded.parameters;
  const problems = showProblems
    ? [...findProblems(draft.subject, draft.body, allowed), ...serverProblems].filter(
        (problem, index, all) =>
          all.findIndex(
            (other) =>
              other.field === problem.field &&
              other.kind === problem.kind &&
              other.parameter === problem.parameter,
          ) === index,
      )
    : [];
  const subjectError = problemText(problems.filter((problem) => problem.field === "subject"));
  const bodyError = problemText(problems.filter((problem) => problem.field === "body_html"));

  const refreshAll = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: keys.emailTemplates(workspace.id) }),
      queryClient.invalidateQueries({ queryKey: versionsQueryKey }),
    ]);
  };

  async function save() {
    setShowProblems(true);
    setServerProblems([]);
    if (findProblems(draft.subject, draft.body, allowed).length) return;
    setSaving(true);
    try {
      const saved = unwrap(
        await api.PUT("/v1/email-templates/{key}", {
          params: { path: { key: templateKey } },
          body: { subject: draft.subject, body_html: draft.body },
        }),
      );
      queryClient.setQueryData(templateQueryKey, saved);
      setDirty(false);
      await refreshAll();
      toast({ title: t("emailTemplates.editor.saved"), tone: "success" });
      router.push("/settings/email-templates");
    } catch (error) {
      if (error instanceof ApiError && error.code === "email_template_invalid") {
        setServerProblems(apiProblems(error.errors));
      } else {
        toast({ title: t("emailTemplates.editor.saveFailed"), tone: "error" });
      }
    } finally {
      setSaving(false);
    }
  }

  async function replaceWith(request: () => Promise<EmailTemplate>, done: string, failed: string) {
    try {
      const next = await request();
      queryClient.setQueryData(templateQueryKey, next);
      load(next);
      await refreshAll();
      toast({ title: done, tone: "success" });
    } catch {
      toast({ title: failed, tone: "error" });
    }
  }

  const reset = () =>
    replaceWith(
      async () =>
        unwrap(
          await api.POST("/v1/email-templates/{key}/reset", {
            params: { path: { key: templateKey } },
          }),
        ),
      t("emailTemplates.resetDialog.done"),
      t("emailTemplates.resetDialog.failed"),
    );

  const restore = (version: EmailTemplateVersion) =>
    replaceWith(
      async () =>
        unwrap(
          await api.POST("/v1/email-templates/{key}/versions/{version_id}/restore", {
            params: { path: { key: templateKey, version_id: version.id } },
          }),
        ),
      t("emailTemplates.editor.restored"),
      t("emailTemplates.editor.restoreFailed"),
    );

  function view(version: EmailTemplateVersion, index: number) {
    // The newest version is the wording in use: back to the draft.
    if (index === 0) {
      if (viewing) {
        setViewing(null);
        setContentKey((value) => value + 1);
      }
      return;
    }
    setViewing(version);
    setContentKey((value) => value + 1);
  }

  function backToCurrent() {
    setViewing(null);
    setContentKey((value) => value + 1);
  }

  const reviewFooter =
    loaded.review_line && !hasReviewLink(shown.body) ? (
      <div className="flex flex-col gap-1 border-t border-dashed border-line px-4 py-3 md:px-[18px]">
        <p className="fh-message text-ink-muted">
          <LockSimpleIcon aria-hidden="true" className="mr-1.5 inline size-4 align-[-2px]" />
          {t("emailTemplates.editor.reviewLine")}{" "}
          <span className="fh-parameter">[{REVIEW_LINK}]</span>
        </p>
        <p className="text-[13px] leading-[18px] text-ink-muted">
          {t("emailTemplates.editor.reviewLineHint")}
        </p>
      </div>
    ) : null;

  return (
    <div className="flex flex-col">
      <header className="page-gutter flex flex-col gap-4 border-b border-line py-5 lg:flex-row lg:items-end lg:justify-between lg:px-10">
        <div className="flex min-w-0 flex-col gap-2">
          <nav
            aria-label={t("emailTemplates.editor.breadcrumb")}
            className="flex items-center gap-2 text-[13px] text-ink-muted"
          >
            <Link href="/settings/email-templates" className="font-semibold text-evergreen">
              {t("emailTemplates.title")}
            </Link>
            <span aria-hidden="true">/</span>
            <span aria-current="page" className="truncate">
              {name}
            </span>
          </nav>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <h1 className="type-heading">{name}</h1>
            <Badge tone={CATEGORY_TONE[category]}>{t(`emailTemplates.category.${category}`)}</Badge>
          </div>
          <p className="flex items-start gap-1.5 text-[14px] text-ink-muted">
            <ClockIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            {t("emailTemplates.editor.sentWhen", {
              timing: timing.charAt(0).toLowerCase() + timing.slice(1),
            })}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:flex sm:items-center sm:gap-3">
          <Button
            variant="quiet"
            className="col-span-2 sm:col-span-1"
            icon={<ArrowCounterClockwiseIcon aria-hidden="true" />}
            disabled={loaded.is_default || Boolean(viewing)}
            onClick={() => setResetOpen(true)}
          >
            {t("emailTemplates.editor.reset")}
          </Button>
          <Link
            href="/settings/email-templates"
            className="inline-flex min-h-11 items-center justify-center rounded-md border border-line-strong bg-surface-raised px-5 text-[15px] font-semibold text-ink hover:border-ink"
          >
            {t("emailTemplates.editor.cancel")}
          </Link>
          <Button
            loading={saving}
            disabled={!dirty || Boolean(viewing)}
            onClick={() => void save()}
          >
            {t("emailTemplates.editor.save")}
          </Button>
        </div>
      </header>

      <div className="page-gutter flex flex-col gap-6 py-6 lg:flex-row lg:items-start lg:px-10">
        <section
          aria-label={t("emailTemplates.editor.contentLabel")}
          className="flex min-w-0 flex-1 flex-col gap-5 rounded-lg border border-line bg-surface-raised p-4 md:p-6"
        >
          {viewing && (
            <div
              role="status"
              className="flex flex-col gap-3 rounded-[8px] bg-persimmon-soft px-4 py-3 md:flex-row md:items-center md:justify-between"
            >
              <p className="text-[14px] leading-5">
                {t("emailTemplates.editor.viewingOld", {
                  when: formatDateTime(viewing.created_at, browserTimeZone()),
                })}
              </p>
              <div className="flex shrink-0 gap-2">
                <Button size="sm" variant="quiet" onClick={backToCurrent}>
                  {t("emailTemplates.editor.backToCurrent")}
                </Button>
                <Button size="sm" onClick={() => void restore(viewing)}>
                  {t("emailTemplates.editor.restore")}
                </Button>
              </div>
            </div>
          )}

          <Field label={t("emailTemplates.editor.subject")} error={subjectError}>
            <Input
              value={shown.subject}
              readOnly={Boolean(viewing)}
              maxLength={1000}
              className="h-12"
              onChange={(event) => {
                setDraft({ ...draft, subject: event.target.value });
                setDirty(true);
              }}
            />
          </Field>

          <div className="flex flex-col gap-1.5">
            <span id={messageLabelId} className="text-[14px] leading-5 font-semibold">
              {t("emailTemplates.editor.message")}
            </span>
            <RichTextEditor
              ref={editorRef}
              value={shown.body}
              contentKey={String(contentKey)}
              editable={!viewing}
              parameters={insertable(allowed)}
              labelledBy={messageLabelId}
              describedBy={bodyError ? messageErrorId : undefined}
              invalid={Boolean(bodyError)}
              footer={reviewFooter}
              onChange={(body) => {
                setDraft((current) => ({ ...current, body }));
                setDirty(true);
              }}
            />
            {bodyError && (
              <p
                id={messageErrorId}
                role="alert"
                className="text-[13px] leading-[18px] font-semibold text-signal-gap"
              >
                {bodyError}
              </p>
            )}
            <p className="text-[13px] leading-[18px] text-ink-muted">
              {t("emailTemplates.editor.parametersNote")}
            </p>
          </div>

          <div className="flex flex-col gap-3 border-t border-line pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-[13px] text-ink-muted">
              {loaded.is_default || !loaded.updated_by
                ? t("emailTemplates.editor.usingDefault")
                : t("emailTemplates.editor.lastEdited", {
                    date: formatDate(loaded.updated_at, browserTimeZone()),
                    name: loaded.updated_by.name || t("emailTemplates.editor.someone"),
                  })}
            </p>
            <Button
              variant="secondary"
              size="sm"
              className="min-h-11 sm:min-h-10"
              icon={<PaperPlaneTiltIcon aria-hidden="true" />}
              onClick={() => {
                setTestRun((run) => run + 1);
                setTestOpen(true);
              }}
            >
              {t("emailTemplates.editor.sendTest")}
            </Button>
          </div>
        </section>

        <div className="flex w-full flex-col gap-4 lg:w-[300px] lg:shrink-0">
          {!viewing && (
            <aside
              aria-labelledby="params-heading"
              className="flex flex-col gap-2 rounded-lg border border-line bg-surface-raised px-3 py-4"
            >
              <div className="flex flex-col gap-1 px-3">
                <h2 id="params-heading" className="text-[15px] font-[650]">
                  {t("emailTemplates.editor.paramsTitle")}
                </h2>
                <p className="text-[13px] leading-[18px] text-ink-muted">
                  {t("emailTemplates.editor.paramsHint")}
                </p>
              </div>
              <ul className="grid gap-0.5 sm:grid-cols-2 lg:grid-cols-1">
                {insertable(allowed).map((parameter) => (
                  <li key={parameter}>
                    <button
                      type="button"
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => editorRef.current?.insertParameter(parameter)}
                      className="flex min-h-11 w-full flex-col items-start gap-0.5 rounded-[8px] px-3 py-2.5 text-left hover:bg-surface-sunk"
                    >
                      <span className="font-mono text-[13px] leading-5 font-medium text-evergreen">
                        [{parameter}]
                      </span>
                      <span className="text-[12px] leading-4 text-ink-muted">
                        {parameterDescription(parameter)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </aside>
          )}

          <History
            versions={versions}
            loading={versionsLoading}
            viewingId={viewing?.id ?? null}
            onPick={view}
          />
        </div>
      </div>

      <ConfirmDialog
        open={resetOpen}
        onOpenChange={setResetOpen}
        title={t("emailTemplates.resetDialog.title")}
        description={t("emailTemplates.resetDialog.body", { name })}
        cancelLabel={t("emailTemplates.resetDialog.keep")}
        confirmLabel={t("emailTemplates.resetDialog.confirm")}
        onConfirm={reset}
      />

      <TestDialog
        key={testRun}
        open={testOpen}
        onOpenChange={setTestOpen}
        templateKey={templateKey}
        name={name}
        email={user.email}
        company={workspace.name}
        subject={shown.subject}
        body={shown.body}
        blocked={findProblems(shown.subject, shown.body, allowed).length > 0}
      />
    </div>
  );
}

function History({
  versions,
  loading,
  viewingId,
  onPick,
}: {
  versions: EmailTemplateVersion[];
  loading: boolean;
  viewingId: string | null;
  onPick: (version: EmailTemplateVersion, index: number) => void;
}) {
  const zone = browserTimeZone();
  return (
    <section
      aria-labelledby="history-heading"
      className="flex flex-col gap-2 rounded-lg border border-line bg-surface-raised px-3 py-4"
    >
      <h2 id="history-heading" className="px-3 text-[15px] font-[650]">
        {t("emailTemplates.editor.historyTitle")}
      </h2>
      {loading ? (
        <div className="flex flex-col gap-2 px-3">
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
        </div>
      ) : versions.length === 0 ? (
        <p className="px-3 text-[13px] leading-[18px] text-ink-muted">
          {t("emailTemplates.editor.historyEmpty")}
        </p>
      ) : (
        <ol className="flex flex-col gap-0.5">
          {versions.map((version, index) => {
            const current = viewingId ? version.id === viewingId : index === 0;
            const who = version.created_by?.name || t("emailTemplates.editor.someone");
            return (
              <li key={version.id}>
                <button
                  type="button"
                  aria-current={current ? "true" : undefined}
                  onClick={() => onPick(version, index)}
                  className={cn(
                    "flex min-h-11 w-full items-start gap-2.5 rounded-[8px] border px-3 py-2.5 text-left",
                    current
                      ? "border-line bg-surface-sunk"
                      : "border-transparent hover:bg-surface-sunk",
                  )}
                >
                  <Avatar id={version.created_by?.id ?? version.id} name={who} size="sm" />
                  <span className="flex min-w-0 flex-col gap-0.5">
                    <span className="text-[13px] leading-[18px]">
                      <span className="font-semibold">{who}</span>{" "}
                      {t(`emailTemplates.editor.change.${changeOf(versions, index)}`)}
                    </span>
                    <span className="flex items-center gap-1.5 text-[12px] text-ink-muted">
                      {formatDateTime(version.created_at, zone)}
                      {index === 0 && (
                        <Badge tone="evergreen" className="h-[18px] px-1.5 text-[11px]">
                          {t("emailTemplates.editor.historyCurrent")}
                        </Badge>
                      )}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

function TestDialog({
  open,
  onOpenChange,
  templateKey,
  name,
  email,
  company,
  subject,
  body,
  blocked,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  templateKey: TemplateKey;
  name: string;
  email: string;
  company: string;
  subject: string;
  body: string;
  blocked: boolean;
}) {
  const toast = useToast();
  const [state, setState] = useState<"ready" | "sending" | "sent">("ready");
  const [sentTo, setSentTo] = useState(email);

  async function send() {
    setState("sending");
    try {
      const sent = unwrap(
        await api.POST("/v1/email-templates/{key}/test", {
          params: { path: { key: templateKey } },
          body: { subject, body_html: body },
        }),
      );
      setSentTo(sent.to_email);
      setState("sent");
    } catch {
      setState("ready");
      toast({ title: t("emailTemplates.testDialog.failed"), tone: "error" });
    }
  }

  const sent = state === "sent";
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      eyebrow={name}
      leading={
        sent ? (
          <CheckCircleIcon aria-hidden="true" weight="fill" className="size-6 text-evergreen" />
        ) : (
          <PaperPlaneTiltIcon aria-hidden="true" className="size-6 text-evergreen" />
        )
      }
      title={sent ? t("emailTemplates.testDialog.sentTitle") : t("emailTemplates.testDialog.title")}
      footer={
        <>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            {sent ? t("emailTemplates.testDialog.done") : t("emailTemplates.testDialog.cancel")}
          </Button>
          {!sent && (
            <Button loading={state === "sending"} disabled={blocked} onClick={() => void send()}>
              {state === "sending"
                ? t("emailTemplates.testDialog.sending")
                : t("emailTemplates.testDialog.send")}
            </Button>
          )}
        </>
      }
    >
      <dl className="grid grid-cols-1 gap-x-4 gap-y-1 text-[14px] sm:grid-cols-[auto_1fr] sm:gap-y-2">
        <dt className="font-semibold text-ink-muted">{t("emailTemplates.testDialog.to")}</dt>
        <dd className="mb-2 break-all sm:mb-0">
          {email} <span className="text-ink-muted">{t("emailTemplates.testDialog.you")}</span>
        </dd>
        <dt className="font-semibold text-ink-muted">{t("emailTemplates.testDialog.subject")}</dt>
        <dd className="mb-2 sm:mb-0">{sampleSubject(subject, company)}</dd>
        <dt className="font-semibold text-ink-muted">{t("emailTemplates.testDialog.sample")}</dt>
        <dd>
          {SAMPLE.firstName} {SAMPLE.lastName} · {SAMPLE.jobTitle} · {company}
        </dd>
      </dl>
      <p
        role="status"
        aria-live="polite"
        className={cn(
          "mt-4 text-[13px] leading-[18px]",
          sent ? "text-evergreen" : blocked ? "font-semibold text-signal-gap" : "text-ink-muted",
        )}
      >
        {sent
          ? t("emailTemplates.testDialog.sentNote", { email: sentTo })
          : blocked
            ? t("emailTemplates.testDialog.fixFirst")
            : t("emailTemplates.testDialog.note")}
      </p>
    </Dialog>
  );
}

function LoadingEditor() {
  return (
    <div className="page-gutter flex flex-col gap-6 py-6 lg:px-10">
      <Skeleton className="h-20" />
      <div className="flex flex-col gap-6 lg:flex-row">
        <Skeleton className="h-[480px] flex-1 rounded-lg" />
        <Skeleton className="h-[320px] rounded-lg lg:w-[300px]" />
      </div>
    </div>
  );
}

const PARAMETER_DESCRIPTIONS: Record<string, Parameters<typeof t>[0]> = {
  "Candidate.firstname": "emailTemplates.parameters.Candidate.firstname",
  "Candidate.lastname": "emailTemplates.parameters.Candidate.lastname",
  "Job.title": "emailTemplates.parameters.Job.title",
  "Company.name": "emailTemplates.parameters.Company.name",
  "Interview.link": "emailTemplates.parameters.Interview.link",
  "Interview.expiry": "emailTemplates.parameters.Interview.expiry",
  "Review.link": "emailTemplates.parameters.Review.link",
};

function parameterDescription(parameter: string): string {
  const key = PARAMETER_DESCRIPTIONS[parameter];
  return key ? t(key) : "";
}

function problemText(problems: FieldProblem[]): string | undefined {
  if (!problems.length) return undefined;
  return problems
    .map((problem) =>
      problem.kind === "unknown_parameter"
        ? t("emailTemplates.editor.problems.unknown_parameter", {
            parameter: problem.parameter ?? "",
          })
        : t(problemKey(problem)),
    )
    .join(" ");
}

function problemKey(problem: FieldProblem): Parameters<typeof t>[0] {
  switch (`${problem.field}_${problem.kind}`) {
    case "subject_missing":
      return "emailTemplates.editor.problems.subject_missing";
    case "subject_too_long":
      return "emailTemplates.editor.problems.subject_too_long";
    case "body_html_missing":
      return "emailTemplates.editor.problems.body_html_missing";
    case "body_html_too_long":
      return "emailTemplates.editor.problems.body_html_too_long";
    default:
      return "emailTemplates.editor.problems.invalid";
  }
}

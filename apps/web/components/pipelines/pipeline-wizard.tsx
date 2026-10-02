"use client";

import { ArrowLeftIcon, ArrowRightIcon, CaretLeftIcon } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { type ReactNode, useEffect, useRef, useState } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { InterviewStep } from "@/components/pipelines/wizard-interview-step";
import { RoleStep } from "@/components/pipelines/wizard-role-step";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Stepper } from "@/components/ui/stepper";
import { useToast } from "@/components/ui/toast";
import { ApiError, api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";
import {
  BUILT_STEPS,
  blockedHint,
  type DepartmentOption,
  defaultDepartment,
  departmentOptions,
  emptyForm,
  formFromPipeline,
  isEditable,
  type Pipeline,
  saveErrorKey,
  setupFromForm,
  STEPS,
  type WizardForm,
} from "@/lib/pipelines/wizard";

const PIPELINES_PATH = "/pipelines";
const SAVED_NOTE_MS = 3000;

/**
 * The New pipeline wizard (PIPE-002). Without `pipelineId` it starts a new pipeline; the first
 * save creates the draft and moves the URL to its edit page. With one it loads that draft.
 */
export function PipelineWizardPage({ pipelineId }: { pipelineId?: string }) {
  const { workspace } = useShell();
  const isAdmin = workspace.role === "admin";
  const departments = useQuery({
    queryKey: keys.departments(workspace.id),
    queryFn: async () => unwrap(await api.GET("/v1/departments")),
  });
  const pipeline = useQuery({
    queryKey: keys.pipeline(workspace.id, pipelineId ?? ""),
    queryFn: async () =>
      unwrap(
        await api.GET("/v1/pipelines/{pipeline_id}", {
          params: { path: { pipeline_id: pipelineId ?? "" } },
        }),
      ),
    enabled: Boolean(pipelineId),
    // The wizard owns the form once it opens; don't refetch underneath it.
    staleTime: Infinity,
  });

  if (departments.isError || pipeline.isError) {
    const notFound = pipeline.error instanceof ApiError && pipeline.error.status === 404;
    return (
      <Centered>
        <EmptyState
          title={t(notFound ? "pipelines.wizard.notFound" : "pipelines.wizard.loadFailed")}
          action={<BackToPipelines />}
        />
      </Centered>
    );
  }
  if (!departments.data || (pipelineId && !pipeline.data)) return <WizardSkeleton />;
  if (pipeline.data && !isEditable(pipeline.data)) return <Locked />;

  const options = departmentOptions(
    departments.data.departments,
    isAdmin,
    t("departments.noDepartment"),
  );
  return (
    <PipelineWizard
      initial={pipeline.data ?? null}
      departments={options}
      isAdmin={isAdmin}
      initialDepartment={defaultDepartment(options, isAdmin)}
    />
  );
}

function PipelineWizard({
  initial,
  departments,
  isAdmin,
  initialDepartment,
}: {
  initial: Pipeline | null;
  departments: DepartmentOption[];
  isAdmin: boolean;
  initialDepartment: string | null;
}) {
  const { workspace } = useShell();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState<WizardForm>(() =>
    initial ? formFromPipeline(initial) : emptyForm(initialDepartment),
  );
  const [pipelineId, setPipelineId] = useState(initial?.id ?? null);
  // The body last saved, so unchanged steps don't save again.
  const [savedBody, setSavedBody] = useState(() =>
    initial ? JSON.stringify(setupFromForm(formFromPipeline(initial))) : null,
  );
  const [step, setStep] = useState(0);
  const [tried, setTried] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savedNote, setSavedNote] = useState(false);
  const [locked, setLocked] = useState(false);
  const noteTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => () => clearTimeout(noteTimer.current), []);

  const update = (changes: Partial<WizardForm>) =>
    setForm((current) => ({ ...current, ...changes }));
  const blocked = blockedHint(form, step);
  const isNew = !initial || initial.status === "draft";

  /** Saves the draft if anything changed. Returns false when the save failed. */
  async function save(): Promise<boolean> {
    const body = setupFromForm(form);
    const serialized = JSON.stringify(body);
    if (pipelineId && serialized === savedBody) return true;
    setSaving(true);
    try {
      const saved = pipelineId
        ? unwrap(
            await api.PATCH("/v1/pipelines/{pipeline_id}", {
              params: { path: { pipeline_id: pipelineId } },
              body,
            }),
          )
        : unwrap(await api.POST("/v1/pipelines", { body }));
      queryClient.setQueryData(keys.pipeline(workspace.id, saved.id), saved);
      if (!pipelineId) {
        setPipelineId(saved.id);
        // Reloading now opens the draft (shallow: the wizard keeps its state).
        window.history.replaceState(null, "", `${PIPELINES_PATH}/${saved.id}/edit`);
      }
      setSavedBody(serialized);
      setSavedNote(true);
      clearTimeout(noteTimer.current);
      noteTimer.current = setTimeout(() => setSavedNote(false), SAVED_NOTE_MS);
      return true;
    } catch (error) {
      if (error instanceof ApiError && error.code === "pipeline_locked") setLocked(true);
      toast({ title: t(saveErrorKey(error)), tone: "error" });
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function goTo(next: number) {
    if (saving || !(await save())) return;
    setTried(false);
    setStep(next);
    window.scrollTo({ top: 0 });
  }

  function onContinue() {
    if (blocked) {
      setTried(true);
      return;
    }
    void goTo(step + 1);
  }

  if (locked) return <Locked />;

  const stepId = STEPS[step] ?? "role";
  const built = step < BUILT_STEPS;
  const nextId = STEPS[step + 1];
  const hint = blocked
    ? t(blocked)
    : nextId
      ? t("pipelines.wizard.next", { step: t(`pipelines.wizard.steps.${nextId}.label`) })
      : null;

  return (
    <div className="flex min-h-[calc(100dvh-56px)] flex-col md:min-h-[calc(100dvh-64px)] lg:min-h-dvh">
      <header className="page-gutter flex flex-col gap-3 border-b border-line bg-surface-raised py-4 sm:flex-row sm:items-center sm:justify-between lg:px-10 lg:py-5">
        <div className="flex flex-col gap-0.5">
          <Link
            href={PIPELINES_PATH}
            className="inline-flex items-center gap-1 self-start text-[13px] font-semibold text-ink-muted hover:text-ink"
          >
            <CaretLeftIcon aria-hidden="true" className="size-4" />
            {t("pipelines.wizard.back")}
          </Link>
          <h1 className="type-heading">
            {t(isNew ? "pipelines.wizard.newTitle" : "pipelines.wizard.editTitle")}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <span role="status" className="mr-auto text-[13px] text-ink-muted sm:mr-1">
            {saving ? t("pipelines.wizard.saving") : savedNote ? t("pipelines.wizard.saved") : ""}
          </span>
          <Button variant="secondary" size="sm" disabled={saving} onClick={() => void save()}>
            {t("pipelines.wizard.saveDraft")}
          </Button>
          <Link
            href={PIPELINES_PATH}
            className="inline-flex min-h-9 items-center rounded-[10px] px-3 text-[13px] font-semibold text-evergreen hover:bg-evergreen-soft"
          >
            {t("pipelines.wizard.cancel")}
          </Link>
        </div>
      </header>

      <div className="page-gutter flex flex-1 flex-col gap-5 py-5 md:py-8 xl:flex-row xl:gap-10 lg:px-10">
        <Stepper
          label={t("pipelines.wizard.stepsLabel")}
          expandAt="xl"
          current={step}
          onStepClick={(index) => void goTo(index)}
          steps={STEPS.map((id) => ({
            label: t(`pipelines.wizard.steps.${id}.label`),
            hint: t(`pipelines.wizard.steps.${id}.hint`),
          }))}
          className="xl:sticky xl:top-8 xl:w-[272px] xl:shrink-0 xl:self-start"
        />

        <section
          aria-labelledby="wizard-step-title"
          className="flex min-w-0 flex-1 flex-col gap-6 xl:max-w-[760px]"
        >
          <div className="flex flex-col gap-1.5">
            <span className="hidden type-label text-ink-muted xl:block">
              {t("pipelines.wizard.stepOf", { step: step + 1, total: STEPS.length })}
            </span>
            <h2 id="wizard-step-title" className="type-title">
              {t(`pipelines.wizard.steps.${stepId}.title`)}
            </h2>
            <p className="type-body text-ink-muted">
              {t(`pipelines.wizard.steps.${stepId}.intro`)}
            </p>
          </div>
          <div className="rounded-lg border border-line bg-surface-raised p-4 sm:p-6 md:p-8">
            {stepId === "role" && (
              <RoleStep
                form={form}
                update={update}
                tried={tried}
                departments={departments}
                isAdmin={isAdmin}
              />
            )}
            {stepId === "interview" && <InterviewStep form={form} update={update} tried={tried} />}
            {!built && (
              <EmptyState
                title={t("pipelines.wizard.comingTitle")}
                description={t("pipelines.wizard.comingBody")}
                action={<BackToPipelines />}
              />
            )}
          </div>
        </section>
      </div>

      <footer className="sticky bottom-0 z-20 border-t border-line bg-surface-raised safe-bottom">
        <div className="page-gutter flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between lg:px-10">
          {hint && (
            <p
              id="wizard-next-hint"
              className={cn(
                "text-[13px] sm:order-2 sm:ml-auto",
                // Blocked: shown on every size, red once Continue was tried.
                blocked ? "font-semibold" : "hidden sm:block",
                blocked && tried ? "text-signal-gap" : "text-ink-muted",
              )}
            >
              {built ? hint : null}
            </p>
          )}
          <div className="flex items-center justify-between gap-3 sm:contents">
            <Button
              variant="secondary"
              icon={<ArrowLeftIcon aria-hidden="true" className="size-4" />}
              disabled={step === 0 || saving}
              onClick={() => void goTo(step - 1)}
              className="sm:order-1"
            >
              {t("pipelines.wizard.previous")}
            </Button>
            {built && (
              <Button
                aria-describedby={hint ? "wizard-next-hint" : undefined}
                loading={saving}
                onClick={onContinue}
                className="sm:order-3"
              >
                {t("pipelines.wizard.continue")}
                <ArrowRightIcon aria-hidden="true" className="size-4" />
              </Button>
            )}
          </div>
        </div>
      </footer>
    </div>
  );
}

function BackToPipelines() {
  return (
    <Link
      href={PIPELINES_PATH}
      className="inline-flex min-h-11 items-center rounded-md bg-evergreen px-5 text-[15px] font-semibold text-on-evergreen hover:brightness-110"
    >
      {t("pipelines.wizard.goToPipelines")}
    </Link>
  );
}

function Centered({ children }: { children: ReactNode }) {
  return <div className="page-gutter py-10 md:py-16">{children}</div>;
}

function Locked() {
  return (
    <Centered>
      <EmptyState
        title={t("pipelines.wizard.lockedTitle")}
        description={t("pipelines.wizard.lockedBody")}
        action={<BackToPipelines />}
      />
    </Centered>
  );
}

function WizardSkeleton() {
  return (
    <div aria-busy="true" className="page-gutter flex flex-col gap-6 py-6 lg:px-10">
      <Skeleton className="h-8 w-48" />
      <div className="flex gap-10">
        <Skeleton className="hidden h-80 w-[272px] xl:block" />
        <Skeleton className="h-[480px] flex-1 rounded-lg" />
      </div>
      <p role="status" className="sr-only">
        {t("app.loading")}
      </p>
    </div>
  );
}

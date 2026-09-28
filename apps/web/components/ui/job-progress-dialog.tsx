"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { t } from "@/lib/i18n";

export type JobState = "queued" | "running" | "succeeded" | "failed";

export interface JobStatus {
  state: JobState;
  /** 0–100 when the job reports it; otherwise the bar is indeterminate. */
  progress?: number;
}

export interface JobProgressDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  /** What is happening, e.g. "We're building the PDF report." */
  description: string;
  /** Called every `intervalMs` until the job succeeds or fails. */
  poll: () => Promise<JobStatus>;
  onSucceeded: () => void;
  onRetry?: () => void;
  intervalMs?: number;
}

/**
 * Waits on a background job (reports, PDFs, bulk actions). While it runs the dialog can't be
 * dismissed and the browser warns before leaving, with "Please don't close or refresh this window."
 */
export function JobProgressDialog(props: JobProgressDialogProps) {
  // Mounting the run only while open gives every run a fresh status.
  return props.open ? <JobRun {...props} /> : null;
}

function JobRun({
  onOpenChange,
  title,
  description,
  poll,
  onSucceeded,
  onRetry,
  intervalMs = 1500,
}: JobProgressDialogProps) {
  const [status, setStatus] = useState<JobStatus>({ state: "queued" });
  const pollRef = useRef(poll);
  const doneRef = useRef(onSucceeded);
  useEffect(() => {
    pollRef.current = poll;
    doneRef.current = onSucceeded;
  });

  const running = status.state === "queued" || status.state === "running";

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      let next: JobStatus;
      try {
        next = await pollRef.current();
      } catch {
        next = { state: "failed" };
      }
      if (stopped) return;
      setStatus(next);
      if (next.state === "succeeded") doneRef.current();
      else if (next.state !== "failed") timer = setTimeout(() => void tick(), intervalMs);
    };
    void tick();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [intervalMs]);

  useEffect(() => {
    if (!running) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [running]);

  const failed = status.state === "failed";
  const progress = status.progress;

  return (
    <Dialog
      open
      onOpenChange={onOpenChange}
      title={title}
      description={failed ? t("ui.jobFailed") : description}
      size="sm"
      dismissible={!running}
      footer={
        failed ? (
          <>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              {t("ui.close")}
            </Button>
            {onRetry && <Button onClick={onRetry}>{t("ui.tryAgain")}</Button>}
          </>
        ) : undefined
      }
    >
      {!failed && (
        <div className="flex flex-col gap-3 pb-4">
          <div
            role="progressbar"
            aria-label={title}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress}
            className="h-2 overflow-hidden rounded-pill bg-surface-sunk"
          >
            <div
              className="h-full rounded-pill bg-evergreen transition-[width] duration-300 ease-out"
              style={{ width: progress === undefined ? "30%" : `${Math.max(4, progress)}%` }}
            />
          </div>
          <p className="flex items-center gap-2 text-[14px] text-ink-muted">
            <Spinner className="size-4" />
            {t("ui.jobKeepOpen")}
          </p>
        </div>
      )}
    </Dialog>
  );
}

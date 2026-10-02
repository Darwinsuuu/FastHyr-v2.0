"use client";

import { FileArrowUpIcon, FileTextIcon, XIcon } from "@phosphor-icons/react";
import { type DragEvent, useId, useRef, useState } from "react";

import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";
import { formatBytes } from "@/lib/format";

export interface FileDropProps {
  /** MIME types, e.g. ["application/pdf"]. */
  accept: string[];
  /** Bytes. */
  maxSize: number;
  file: File | null;
  onFileChange: (file: File | null) => void;
  /** Line under the prompt, e.g. "PDF, up to 10 MB". */
  hint: string;
  label?: string;
  /** A problem found elsewhere, e.g. "Add your résumé as a PDF to continue." or the server's
   * check of the file. Shown like the type and size errors. */
  error?: string;
  disabled?: boolean;
  className?: string;
}

/** Returns an error message for a file that doesn't fit, or null. */
export function checkFile(file: File, accept: string[], maxSize: number): string | null {
  if (!accept.includes(file.type)) return t("ui.fileTypeNotSupported");
  if (file.size > maxSize) return t("ui.fileTooLarge", { size: formatBytes(maxSize) });
  return null;
}

/** Drop a file or choose one. Checks type and size before handing the file up. Tapping works on phones. */
export function FileDrop({
  accept,
  maxSize,
  file,
  onFileChange,
  hint,
  label = t("ui.dropFile"),
  error: outsideError,
  disabled,
  className,
}: FileDropProps) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [checkError, setError] = useState<string | null>(null);
  const error = checkError ?? outsideError ?? null;
  const errorLine = error && (
    <p
      id={`${id}-error`}
      role="alert"
      className="mt-1.5 text-[13px] leading-[18px] font-semibold text-signal-gap"
    >
      {error}
    </p>
  );

  function take(candidate: File | undefined) {
    if (!candidate) return;
    const problem = checkFile(candidate, accept, maxSize);
    setError(problem);
    if (!problem) onFileChange(candidate);
  }

  function onDrop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    if (!disabled) take(event.dataTransfer.files[0]);
  }

  if (file) {
    return (
      <div className={className}>
        <div
          className={cn(
            "flex items-center gap-3 rounded-md border border-line bg-surface-raised p-3",
            error && "border-signal-gap",
          )}
        >
          <FileTextIcon aria-hidden="true" className="size-6 shrink-0 text-evergreen" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-[15px] font-semibold text-ink">{file.name}</p>
            <p className="text-[13px] text-ink-muted">{formatBytes(file.size)}</p>
          </div>
          <button
            type="button"
            disabled={disabled}
            aria-label={t("ui.remove", { label: file.name })}
            onClick={() => onFileChange(null)}
            className="flex size-11 items-center justify-center rounded-[10px] text-ink-muted hover:bg-surface-sunk hover:text-ink"
          >
            <XIcon aria-hidden="true" className="size-5" />
          </button>
        </div>
        {errorLine}
      </div>
    );
  }

  return (
    <div className={className}>
      <label
        htmlFor={id}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          "flex min-h-36 cursor-pointer flex-col items-center justify-center gap-2 rounded-md border-[1.5px] border-dashed border-line-strong bg-surface-raised p-6 text-center",
          "transition-colors duration-200 ease-out hover:border-ink has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-focus",
          dragging && "border-evergreen bg-evergreen-soft",
          error && "border-signal-gap",
          disabled && "cursor-not-allowed opacity-60",
        )}
      >
        <FileArrowUpIcon aria-hidden="true" className="size-8 text-ink-muted" />
        <span className="text-[15px] font-semibold text-ink">{label}</span>
        <span className="text-[13px] text-ink-muted">{hint}</span>
        <input
          ref={input}
          id={id}
          type="file"
          accept={accept.join(",")}
          disabled={disabled}
          aria-describedby={error ? `${id}-error` : undefined}
          className="sr-only"
          onChange={(event) => {
            take(event.target.files?.[0]);
            event.target.value = "";
          }}
        />
      </label>
      {errorLine}
    </div>
  );
}

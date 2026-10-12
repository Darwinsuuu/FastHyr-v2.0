"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { type ApplicationProfile, clock } from "@/lib/candidates/profile";
import { t } from "@/lib/i18n";

// Signed links last 15 minutes; read a fresh one well before that.
const STALE_MS = 10 * 60_000;

/**
 * The AI interview tab's recording, opened at `seconds` when an evidence time sent the member
 * here. A plain player for now: topic markers, the topics list, the transcript and keyboard
 * controls arrive with ASMT-006.
 */
export function ProfileRecording({
  profile,
  seconds,
}: {
  profile: ApplicationProfile;
  seconds: number | null;
}) {
  const { workspace } = useShell();
  const ready = Boolean(profile.interview?.recording_ready);
  const query = useQuery({
    queryKey: keys.recordingUrl(workspace.id, profile.id),
    queryFn: async () =>
      unwrap(
        await api.GET("/v1/applications/{application_id}/recording-url", {
          params: { path: { application_id: profile.id } },
        }),
      ),
    enabled: ready,
    staleTime: STALE_MS,
    refetchInterval: STALE_MS,
    // A 404 means the files aren't there (yet): asking again won't change that.
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 2,
  });
  const missing = query.error instanceof ApiError && query.error.status === 404;
  const media = useRef<HTMLVideoElement & HTMLAudioElement>(null);

  // Seek whenever the moment in the URL changes (and once the media can seek).
  useEffect(() => {
    const element = media.current;
    if (!element || seconds === null) return;
    const apply = () => {
      element.currentTime = seconds;
    };
    if (element.readyState >= 1) apply();
    else element.addEventListener("loadedmetadata", apply, { once: true });
    return () => element.removeEventListener("loadedmetadata", apply);
  }, [seconds, query.data?.url]);

  let body;
  if (!ready || missing) {
    body = <Note>{t("candidates.profile.recording.notReady")}</Note>;
  } else if (query.isError) {
    body = (
      <div className="flex flex-col items-start gap-3">
        <Note>{t("candidates.profile.recording.failed")}</Note>
        <Button variant="secondary" size="sm" onClick={() => void query.refetch()}>
          {t("candidates.profile.recording.retry")}
        </Button>
      </div>
    );
  } else if (!query.data) {
    body = <Skeleton className="aspect-video w-full rounded-md" />;
  } else if (query.data.kind === "video") {
    body = (
      <video
        ref={media}
        key={query.data.url}
        src={query.data.url}
        poster={query.data.poster_url ?? undefined}
        controls
        preload="metadata"
        playsInline
        aria-label={t("candidates.profile.recording.video")}
        className="aspect-video w-full rounded-md bg-ink"
      />
    );
  } else {
    body = (
      <audio
        ref={media}
        key={query.data.url}
        src={query.data.url}
        controls
        preload="metadata"
        aria-label={t("candidates.profile.recording.audio")}
        className="w-full"
      />
    );
  }

  return (
    <section
      aria-labelledby="profile-recording"
      className="flex flex-col gap-4 rounded-lg border border-line bg-surface-raised p-4 md:p-5"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="profile-recording" className="type-title">
          {t("candidates.profile.recording.title")}
        </h2>
        {seconds !== null && ready && (
          <span className="text-[13px] text-ink-muted tabular-nums">
            {t("candidates.profile.recording.startsAt", { time: clock(seconds * 1000) })}
          </span>
        )}
      </div>
      {body}
      <p className="text-[13px] leading-[18px] text-ink-muted">
        {t("candidates.profile.recording.more")}
      </p>
    </section>
  );
}

function Note({ children }: { children: string }) {
  return <p className="text-[15px] leading-6 text-ink-muted">{children}</p>;
}

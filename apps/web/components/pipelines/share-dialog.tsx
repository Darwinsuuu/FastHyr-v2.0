"use client";

import { useQuery } from "@tanstack/react-query";
import type { RefObject } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { ShareTiles } from "@/components/pipelines/share-tiles";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { t } from "@/lib/i18n";
import { shareLinksBySource } from "@/lib/pipelines/share";
import { SHARE_SOURCES } from "@/lib/pipelines/wizard";

/** The share modal (frame PipelinesV2 / PipelineView, FR-PIPE-10): the wizard's share tiles with
 * the links the API builds for this pipeline. Opened from Copy apply link in the row and header
 * menus and from the details header's Share apply link. */
export function ShareDialog({
  pipelineId,
  title,
  onOpenChange,
  returnFocusTo,
}: {
  pipelineId: string;
  title: string;
  onOpenChange: (open: boolean) => void;
  returnFocusTo?: RefObject<HTMLElement | null>;
}) {
  const { workspace } = useShell();
  const query = useQuery({
    queryKey: keys.pipelineShareLinks(workspace.id, pipelineId),
    queryFn: async () =>
      unwrap(
        await api.GET("/v1/pipelines/{pipeline_id}/share-links", {
          params: { path: { pipeline_id: pipelineId } },
        }),
      ),
    // A pipeline's slugs never change once it's published.
    staleTime: Infinity,
  });

  return (
    <Dialog
      open
      onOpenChange={onOpenChange}
      size="lg"
      eyebrow={t("pipelines.share.eyebrow")}
      title={t("pipelines.share.title", { title })}
      description={t("pipelines.share.body")}
      returnFocusTo={returnFocusTo}
    >
      <div className="pb-4 md:pb-5">
        {query.data ? (
          <ShareTiles links={shareLinksBySource(query.data.links)} />
        ) : query.isError ? (
          <div role="alert" className="flex flex-col items-start gap-3 py-4">
            <p className="text-[15px] text-ink-muted">{t("pipelines.share.loadFailed")}</p>
            <Button variant="secondary" onClick={() => void query.refetch()}>
              {t("pipelines.share.retry")}
            </Button>
          </div>
        ) : (
          <ul
            aria-busy="true"
            aria-label={t("pipelines.share.loading")}
            className="grid grid-cols-2 gap-3 sm:grid-cols-4"
          >
            {SHARE_SOURCES.map((source) => (
              <li key={source}>
                <Skeleton className="h-[104px] w-full rounded-md" />
              </li>
            ))}
          </ul>
        )}
      </div>
    </Dialog>
  );
}

"use client";

import { QueryClient, QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import { type ReactNode, useCallback, useState } from "react";

import { ApiError } from "@/lib/api/client";
import { workspaceCookie } from "@/lib/workspace";
import { activateWorkspace } from "@/lib/workspaces/activate";

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        // Don't retry what won't change on retry: sign-in, membership, permission, not found.
        retry: (failureCount, error) =>
          !(error instanceof ApiError && error.status >= 400 && error.status < 500) &&
          failureCount < 2,
      },
    },
  });
}

export function ApiProvider({ children }: { children: ReactNode }) {
  const [client] = useState(makeQueryClient);
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

/**
 * Switches the active workspace: the `fh_ws` cookie and last workspace (activateWorkspace), then
 * clears every cached query so nothing from the previous workspace shows. `null` forgets it.
 */
export function useSwitchWorkspace() {
  const queryClient = useQueryClient();
  return useCallback(
    async (workspaceId: string | null) => {
      if (workspaceId) {
        await activateWorkspace(workspaceId);
      } else {
        document.cookie = workspaceCookie(null);
      }
      queryClient.clear();
    },
    [queryClient],
  );
}

"use client";

import { QueryClient, QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import { type ReactNode, useCallback, useState } from "react";

import { ApiError } from "@/lib/api/client";
import { workspaceCookie } from "@/lib/workspace";

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

/** Switches the active workspace: replaces the `fh_ws` cookie and clears every cached query. */
export function useSwitchWorkspace() {
  const queryClient = useQueryClient();
  return useCallback(
    (workspaceId: string | null) => {
      document.cookie = workspaceCookie(workspaceId);
      queryClient.clear();
    },
    [queryClient],
  );
}

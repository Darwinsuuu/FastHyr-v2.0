"use client";

import { useQuery } from "@tanstack/react-query";

import { keys } from "@/lib/api/keys";
import { loadNotices } from "@/lib/notices";

/** The current notices for client components. They change only with a release, so they're
 * fetched once per page load. */
export function useNotices() {
  return useQuery({ queryKey: keys.notices(), queryFn: loadNotices, staleTime: Infinity });
}

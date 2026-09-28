"use client";

import { useSyncExternalStore } from "react";

/** True when the media query matches. Server render assumes a phone (mobile first). */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const list = window.matchMedia(query);
      list.addEventListener("change", onChange);
      return () => list.removeEventListener("change", onChange);
    },
    () => window.matchMedia(query).matches,
    () => false,
  );
}

/** Tailwind's `md` breakpoint (768 px): tablets and up. */
export const useIsTabletUp = () => useMediaQuery("(min-width: 768px)");

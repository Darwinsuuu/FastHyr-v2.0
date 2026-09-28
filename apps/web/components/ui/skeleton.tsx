import { cn } from "@/lib/cn";

/** A placeholder block while data loads. Pair a group of them with one aria-busy container. */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "h-4 rounded-sm bg-surface-sunk animate-[fh-shimmer_1.6s_ease-in-out_infinite]",
        className,
      )}
    />
  );
}

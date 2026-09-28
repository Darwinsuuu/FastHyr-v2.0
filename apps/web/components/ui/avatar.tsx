import { cn } from "@/lib/cn";

// Colour pairs from the frames (background / text), picked by a stable hash of the id.
const PAIRS = [
  "bg-sage text-ink",
  "bg-persimmon-soft text-persimmon-ink",
  "bg-evergreen-soft text-evergreen",
  "bg-surface-sunk text-ink",
];

const SIZES = { sm: "size-7 text-[11px]", md: "size-9 text-[13px]", lg: "size-12 text-[16px]" };

/** Up to two initials: first letters of the first and last words. */
export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  const first = words[0]?.[0] ?? "";
  const last = words.length > 1 ? (words[words.length - 1]?.[0] ?? "") : "";
  return (first + last).toUpperCase();
}

/** Picks a colour pair from an id so a person keeps the same colour everywhere. */
export function pairIndex(id: string): number {
  let hash = 0;
  for (const char of id) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return hash % PAIRS.length;
}

export interface AvatarProps {
  /** Stable id (user or member id), used only to pick the colour. */
  id: string;
  name: string;
  /** A photo URL (TA members only; candidates never have photos shown in review). */
  src?: string | null;
  size?: keyof typeof SIZES;
  className?: string;
}

/** A person: their photo, or initials on one of the frame colour pairs. Decorative next to a visible name. */
export function Avatar({ id, name, src, size = "md", className }: AvatarProps) {
  const base = cn(
    "inline-flex shrink-0 items-center justify-center overflow-hidden rounded-pill font-semibold",
    SIZES[size],
    className,
  );
  if (src) {
    // eslint-disable-next-line @next/next/no-img-element -- small remote avatars, no optimisation needed
    return <img src={src} alt="" className={cn(base, "object-cover")} />;
  }
  return (
    <span aria-hidden="true" className={cn(base, PAIRS[pairIndex(id)])}>
      {initials(name)}
    </span>
  );
}

/** A workspace: rounded square with its initials on evergreen. */
export function WorkspaceAvatar({
  name,
  size = "md",
  className,
}: {
  name: string;
  size?: keyof typeof SIZES;
  className?: string;
}) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-[8px] bg-evergreen font-semibold text-on-evergreen",
        SIZES[size],
        className,
      )}
    >
      {initials(name)}
    </span>
  );
}

import { cn } from "@/lib/cn";

/**
 * The Turn: FastHyr's mark, two half-rounds facing each other (the asking half larger and higher).
 * Drawn with token fills, so Night gets the reversed inks automatically. Decorative unless `title` is set.
 */
export function TurnMark({
  size = 32,
  title,
  className,
}: {
  size?: number;
  title?: string;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 56 56"
      width={size}
      height={size}
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      className={cn("shrink-0", className)}
    >
      {title && <title>{title}</title>}
      <path d="M26 4 A20 20 0 0 0 26 44 Z" className="fill-evergreen" />
      <path d="M30 14 A16 16 0 0 1 30 46 Z" className="fill-persimmon" />
    </svg>
  );
}

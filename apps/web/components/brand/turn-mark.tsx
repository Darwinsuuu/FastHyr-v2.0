import { cn } from "@/lib/cn";

/**
 * The Turn: FastHyr's mark, two half-rounds facing each other (the asking half larger and higher).
 * Drawn with token fills, so Night gets the reversed inks automatically. Decorative unless `title` is set.
 * `reversed` is for evergreen grounds (the sign-in panel): the asking half takes the panel's ink.
 */
export function TurnMark({
  size = 32,
  title,
  reversed = false,
  className,
}: {
  size?: number;
  title?: string;
  reversed?: boolean;
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
      <path
        d="M26 4 A20 20 0 0 0 26 44 Z"
        className={reversed ? "fill-on-evergreen" : "fill-evergreen"}
      />
      <path d="M30 14 A16 16 0 0 1 30 46 Z" className="fill-persimmon" />
    </svg>
  );
}

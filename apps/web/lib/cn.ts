import { type ClassValue, clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

// tailwind-merge must know our token-named text styles are font sizes, not colours, or it
// would drop `text-ink` when a `text-body-sm` follows it.
const merge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [
        {
          text: [
            "display-xl",
            "display-lg",
            "question",
            "heading",
            "title",
            "body",
            "body-sm",
            "label",
            "mono",
          ],
        },
      ],
    },
  },
});

/** Joins class names; later Tailwind classes win over earlier ones in the same group. */
export function cn(...inputs: ClassValue[]): string {
  return merge(clsx(inputs));
}

// Checks the colour token pairs the UI kit uses against WCAG 2.2 in both themes (FND-012).
// Text needs 4.5:1; control borders, tracks and the focus ring need 3:1. Run by `pnpm --filter web lint`.
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const SOURCE = resolve(here, "../../../docs/design/tokens.json");

// [foreground, background, where it is used]. Add a pair when a component starts using one.
export const TEXT_PAIRS = [
  ["ink", "surface", "page text"],
  ["ink", "surface-raised", "card and input text"],
  ["ink", "surface-sunk", "text on wells, segmented control, neutral pills"],
  ["ink-muted", "surface", "hints on the page"],
  ["ink-muted", "surface-raised", "hints, placeholders, icon buttons"],
  ["ink-muted", "surface-sunk", "tab counts, unselected segments"],
  ["on-evergreen", "evergreen", "primary button (hiring side), Advanced pill"],
  ["on-persimmon", "persimmon", "primary button (candidate side)"],
  ["evergreen", "surface-raised", "quiet button (hiring side)"],
  ["evergreen", "evergreen-soft", "chips, Live pill, avatars, workspace role badge"],
  ["ink", "sage", "avatar initials (evergreen on sage fails in Night)"],
  ["persimmon-ink", "surface-raised", "quiet button (candidate side)"],
  ["persimmon-ink", "persimmon-soft", "badges and avatars"],
  ["signal-gap", "surface-raised", "errors, destructive buttons and menu items"],
  ["signal-gap", "surface", "errors on the page"],
  ["signal-strong", "surface-raised", "Strong evidence"],
  ["signal-watch", "surface-raised", "Worth probing"],
  ["surface-raised", "signal-gap", "destructive primary button"],
  ["surface-raised", "ink", "tooltips and toasts"],
  ["on-marigold", "marigold", "highlighted résumé phrase"],
  ["ink", "persimmon-soft", "question context on the candidate stage"],
];

export const NON_TEXT_PAIRS = [
  ["line-strong", "surface", "control borders on the page"],
  ["line-strong", "surface-raised", "input, checkbox and secondary button borders"],
  ["line-strong", "surface-raised", "toggle track (off)"],
  ["evergreen", "surface-sunk", "slider range, progress bars"],
  ["evergreen", "surface-raised", "checked checkbox and toggle"],
  ["focus", "surface", "focus ring"],
  ["focus", "surface-raised", "focus ring on cards and dialogs"],
];

function luminance(hex) {
  const channels = hex
    .replace("#", "")
    .match(/../g)
    .map((part) => Number.parseInt(part, 16) / 255)
    .map((c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

export function contrast(a, b) {
  const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (light + 0.05) / (dark + 0.05);
}

/** Returns one line per failing pair (empty when everything passes). */
export function checkContrast(tokens) {
  const colors = Object.fromEntries(tokens.color.tokens.map((t) => [t.name, t.value]));
  const failures = [];
  for (const theme of tokens.color.themes.map((t) => t.id)) {
    for (const [pairs, minimum] of [
      [TEXT_PAIRS, 4.5],
      [NON_TEXT_PAIRS, 3],
    ]) {
      for (const [fg, bg, use] of pairs) {
        if (!colors[fg] || !colors[bg]) {
          failures.push(`unknown token in pair ${fg} on ${bg}`);
          continue;
        }
        const ratio = contrast(colors[fg][theme], colors[bg][theme]);
        if (ratio < minimum) {
          failures.push(
            `${theme}: ${fg} on ${bg} is ${ratio.toFixed(2)}:1, needs ${minimum}:1 (${use})`,
          );
        }
      }
    }
  }
  return failures;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const failures = checkContrast(JSON.parse(readFileSync(SOURCE, "utf8")));
  if (failures.length > 0) {
    console.error(`Contrast check failed:\n${failures.map((line) => `  ${line}`).join("\n")}`);
    process.exit(1);
  }
  console.log("Contrast check passed.");
}

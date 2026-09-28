import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

// @ts-expect-error -- plain ESM script without type declarations
import { buildTokensCss } from "./generate-tokens.mjs";

const tokens = JSON.parse(
  readFileSync(new URL("../../../docs/design/tokens.json", import.meta.url), "utf8"),
);
const css: string = buildTokensCss(tokens);

describe("design tokens", () => {
  it("styles/tokens.css is up to date with docs/design/tokens.json", () => {
    expect(readFileSync(new URL("../styles/tokens.css", import.meta.url), "utf8")).toBe(css);
  });

  it("defines every colour for Paper and Night", () => {
    const light = css.slice(css.indexOf(":root {"), css.indexOf('[data-theme="dark"]'));
    const dark = css.slice(css.indexOf('[data-theme="dark"]'), css.indexOf("@media"));
    for (const token of tokens.color.tokens as { name: string; value: Record<string, string> }[]) {
      expect(light).toContain(`--fh-${token.name}: ${token.value.light};`);
      expect(dark).toContain(`--fh-${token.name}: ${token.value.dark};`);
      expect(css).toContain(`--color-${token.name}: var(--fh-${token.name});`);
    }
  });

  it("makes labels uppercase and questions italic", () => {
    expect(css).toMatch(/@utility type-label \{[^}]*text-transform: uppercase;/);
    expect(css).toMatch(/@utility type-question \{[^}]*font-style: italic;/);
  });
});

// WS-005: every app page is gated in the UI by the same rule as its nav item (SECURITY.md §2).
// A page reached by URL shows "no access" to a role its nav item is hidden from, and a page deeper
// in a section never opens to a role that can't see the section.

import { readdirSync, readFileSync } from "node:fs";
import { join, relative, sep } from "node:path";

import { describe, expect, it } from "vitest";

import { NAV, navItemFor } from "./app-nav";
import { type Action, MATRIX, type Role } from "./permissions";

const APP_DIR = join(__dirname, "..", "app", "ta", "(app)");

function pages(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return pages(path);
    return entry.name === "page.tsx" ? [path] : [];
  });
}

/** "/pipelines/[id]/edit" for app/ta/(app)/pipelines/[id]/edit/page.tsx. */
function routeOf(file: string): string {
  const parts = relative(APP_DIR, file).split(sep).slice(0, -1);
  return `/${parts.join("/")}`;
}

/** The action the page gates on: `<RequireAccess action=…>` or `<PagePlaceholder … action=…>`. */
function gateOf(file: string): Action | null {
  const source = readFileSync(file, "utf8");
  const match = /<(?:RequireAccess|PagePlaceholder)\b[^>]*\baction="(\w+)"/.exec(source);
  return match ? (match[1] as Action) : null;
}

const roles = (action: Action) => Object.keys(MATRIX[action]) as Role[];

const PAGES = pages(APP_DIR).map((file) => ({ route: routeOf(file), gate: gateOf(file) }));

describe("app pages", () => {
  it("are all found", () => {
    const routes = PAGES.map((page) => page.route);
    for (const item of NAV.flatMap((section) => section.items)) {
      expect(routes).toContain(item.href);
    }
  });

  it.each(PAGES)("$route gates on a permission", ({ gate }) => {
    expect(gate).not.toBeNull();
  });

  it.each(PAGES)("$route opens to no role its nav item hides", ({ route, gate }) => {
    const item = navItemFor(route);
    expect(item).not.toBeNull();
    if (!item || !gate) return;
    if (item.href === route) {
      expect(gate).toBe(item.action);
    } else {
      const section = roles(item.action);
      for (const role of roles(gate)) expect(section).toContain(role);
    }
  });
});

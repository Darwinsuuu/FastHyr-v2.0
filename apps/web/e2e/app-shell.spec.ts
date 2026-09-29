import { expect, type Page, test } from "@playwright/test";

import { clickUntil } from "./hydration";
import { latestLinkTo } from "./mailpit";

/** Signs up a new TA user and creates each workspace in turn; ends in the last one. */
async function signUpWithWorkspaces(page: Page, names: string[]) {
  const email = `e2e-shell-${Date.now()}-${Math.random().toString(36).slice(2, 6)}@example.com`;
  await page.goto("/login");
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel("Password").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page).toHaveURL(/\/verify-email$/);
  await page.goto(await latestLinkTo(email));
  await expect(page).toHaveURL(/\/workspaces$/);

  for (const [index, name] of names.entries()) {
    if (index > 0) await page.goto("/workspaces");
    const create = page.getByRole("button", { name: "Create workspace" });
    await clickUntil(create, () =>
      expect(page.getByText("Enter a name for your workspace.")).toBeVisible({ timeout: 2000 }),
    );
    await page.getByLabel("Workspace name").fill(name);
    await create.click();
    await expect(page.getByRole("heading", { name: `Welcome to ${name}` })).toBeVisible();
  }
}

test("the sidebar switches workspace and marks the current page", async ({ page }) => {
  const first = `Shell One ${Date.now()}`;
  const second = `Shell Two ${Date.now()}`;
  await signUpWithWorkspaces(page, [first, second]);

  const nav = page.getByRole("navigation", { name: "Main" });
  await nav.getByRole("link", { name: "Pipelines" }).click();
  await expect(page).toHaveURL(/\/pipelines$/);
  await expect(nav.getByRole("link", { name: "Pipelines" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  // An admin sees the admin sections.
  await expect(nav.getByRole("link", { name: "Billing & invoices" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Manage members" })).toBeVisible();

  await page.getByRole("button", { name: `Switch workspace, current: ${second}` }).click();
  const menu = page.getByRole("menu", { name: "Workspaces" });
  await expect(menu.getByRole("menuitemradio", { name: new RegExp(second) })).toHaveAttribute(
    "aria-checked",
    "true",
  );
  await menu.getByRole("menuitemradio", { name: new RegExp(first) }).click();

  // Same section, other workspace.
  await expect(
    page.getByRole("button", { name: `Switch workspace, current: ${first}` }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/pipelines$/);
});

test("on a phone the menu opens as a drawer and the switcher as a sheet", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 });
  const name = `Shell Phone ${Date.now()}`;
  await signUpWithWorkspaces(page, [name]);

  await page.getByRole("button", { name: "Open menu" }).click();
  const drawer = page.getByRole("dialog", { name: "Menu" });
  await drawer.getByRole("link", { name: "Candidates" }).click();
  await expect(drawer).toBeHidden();
  await expect(page.getByRole("heading", { name: "Candidates" })).toBeVisible();

  await page.getByRole("button", { name: `Switch workspace, current: ${name}` }).click();
  const sheet = page.getByRole("dialog", { name: "Workspaces" });
  await expect(sheet.getByText("Create a workspace")).toBeVisible();
  await expect(sheet.getByRole("button", { name: new RegExp(name) })).toHaveAttribute(
    "aria-current",
    "true",
  );
});

import { expect, test } from "@playwright/test";

import { clickUntil } from "./hydration";
import { latestLinkTo } from "./mailpit";

test("the owner sees themselves on Manage members, with their access locked", async ({ page }) => {
  const email = `e2e-members-${Date.now()}-${Math.random().toString(36).slice(2, 6)}@example.com`;
  const name = `Members ${Date.now()}`;
  await page.goto("/login");
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel("Password").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page).toHaveURL(/\/verify-email$/);
  await page.goto(await latestLinkTo(email));
  const create = page.getByRole("button", { name: "Create workspace" });
  await clickUntil(create, () =>
    expect(page.getByText("Enter a name for your workspace.")).toBeVisible({ timeout: 2000 }),
  );
  await page.getByLabel("Workspace name").fill(name);
  await create.click();
  await expect(page.getByRole("heading", { name: `Welcome to ${name}` })).toBeVisible();

  await page
    .getByRole("navigation", { name: "Main" })
    .getByRole("link", { name: "Manage members" })
    .click();
  await expect(page.getByRole("heading", { name: "Manage members" })).toBeVisible();
  const row = page.getByRole("row", { name: new RegExp(email) });
  await expect(row).toContainText("(you)");
  await expect(row).toContainText("Workspace owner");
  await expect(row).toContainText("All departments");
  await expect(row.getByRole("button", { name: /More actions/ })).toHaveCount(0);

  await page.getByPlaceholder("Search by name or email").fill("nobody-here");
  await expect(page.getByText("No members match your search or filters.")).toBeVisible();
});

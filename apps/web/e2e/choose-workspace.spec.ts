import { expect, test } from "@playwright/test";

import { clickUntil } from "./hydration";
import { latestLinkTo } from "./mailpit";

test("a new TA user creates a workspace and lands on Getting started", async ({ page }) => {
  const email = `e2e-ws-${Date.now()}@example.com`;
  const name = `E2E Talent ${Date.now()}`;

  await page.goto("/login");
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel("Password").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page).toHaveURL(/\/verify-email$/);
  await page.goto(await latestLinkTo(email));
  await expect(page).toHaveURL(/\/workspaces$/);

  const create = page.getByRole("button", { name: "Create workspace" });
  await clickUntil(create, () =>
    expect(page.getByText("Enter a name for your workspace.")).toBeVisible({ timeout: 2000 }),
  );
  await page.getByLabel("Workspace name").fill(name);
  await create.click();

  await expect(page).toHaveURL(/app\.fasthyr\.localhost:\d+\/getting-started$/);
  await expect(page.getByRole("heading", { name: `Welcome to ${name}` })).toBeVisible();

  // Back on Choose workspace, the new workspace is listed and opens the app.
  await page.goto("/workspaces");
  await page.getByRole("button", { name: `Open ${name}` }).click();
  await expect(page).toHaveURL(/app\.fasthyr\.localhost:\d+\/overview$/);
});

test("joining with an unknown code explains what went wrong", async ({ page }) => {
  const email = `e2e-join-${Date.now()}@example.com`;

  await page.goto("/login");
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel("Password").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.goto(await latestLinkTo(email));
  await expect(page).toHaveURL(/\/workspaces$/);

  await page.getByLabel("Invite link or code").fill("fasthyr.com/join/NOPE-0000");
  await clickUntil(page.getByRole("button", { name: "Join workspace" }), () =>
    expect(page.getByText("We couldn't find that invite.")).toBeVisible({ timeout: 3000 }),
  );
});

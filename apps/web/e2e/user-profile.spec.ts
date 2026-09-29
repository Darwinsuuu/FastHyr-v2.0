import { expect, type Page, test } from "@playwright/test";

import { clickUntil } from "./hydration";
import { latestLinkTo } from "./mailpit";

/** Signs up a verified email + password user and creates a workspace; ends on its first page. */
async function signUpWithWorkspace(page: Page) {
  const email = `e2e-profile-${Date.now()}-${Math.random().toString(36).slice(2, 6)}@example.com`;
  await page.goto("/login");
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel("Password").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page).toHaveURL(/\/verify-email$/);
  await page.goto(await latestLinkTo(email));
  await expect(page).toHaveURL(/\/workspaces$/);
  return email;
}

test("the account menu opens the user profile, and the user ID copies", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  const email = await signUpWithWorkspace(page);

  const name = `Profile ${Date.now()}`;
  const create = page.getByRole("button", { name: "Create workspace" });
  await clickUntil(create, () =>
    expect(page.getByText("Enter a name for your workspace.")).toBeVisible({ timeout: 2000 }),
  );
  await page.getByLabel("Workspace name").fill(name);
  await create.click();
  await expect(page.getByRole("heading", { name: `Welcome to ${name}` })).toBeVisible();

  const accountButton = page.getByRole("button", { name: `Account: ${email}` });
  await accountButton.click();
  await page.getByRole("menuitem", { name: "User profile" }).click();

  const dialog = page.getByRole("dialog", { name: email });
  await expect(dialog.getByText("Your FastHyr account")).toBeVisible();
  await expect(dialog.getByText("Verified")).toBeVisible();
  await expect(dialog.getByText("Email and password")).toBeVisible();
  await expect(dialog.getByText("Your account uses your email address as its name.")).toBeVisible();

  const userId = await dialog.getByTestId("profile-user-id").innerText();
  expect(userId).toMatch(/^[0-9a-f-]{36}$/);
  await dialog.getByRole("button", { name: "Copy user ID" }).click();
  await expect(dialog.getByRole("button", { name: "Copied" })).toBeVisible();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(userId);

  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(accountButton).toBeFocused();
});

test("the choose workspace page has the user profile too", async ({ page }) => {
  const email = await signUpWithWorkspace(page);

  const accountButton = page.getByRole("button", { name: "Account" });
  const profileItem = page.getByRole("menuitem", { name: "User profile" });
  await clickUntil(accountButton, () => expect(profileItem).toBeVisible({ timeout: 2000 }));
  await profileItem.click();
  const dialog = page.getByRole("dialog", { name: email });
  await expect(dialog.getByText(email, { exact: true })).toBeVisible();
  await dialog.getByRole("button", { name: "Close" }).last().click();
  await expect(dialog).toBeHidden();
  await expect(accountButton).toBeFocused();
});

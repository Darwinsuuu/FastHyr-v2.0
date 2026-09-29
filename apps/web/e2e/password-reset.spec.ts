import { expect, type Page, test } from "@playwright/test";

import { clickUntil } from "./hydration";
import { latestLinkTo } from "./mailpit";

async function continueWithEmail(page: Page, email: string, password: string) {
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Continue", exact: true }).click();
}

test("a TA user resets a forgotten password from the email link", async ({ page, browser }) => {
  const email = `e2e-reset-${Date.now()}@example.com`;

  await page.goto("/login");
  await continueWithEmail(page, email, "first-password-1");
  await page.goto(await latestLinkTo(email, "Verify"));
  await expect(page).toHaveURL(/\/workspaces$/);
  await clickUntil(page.getByRole("button", { name: "Log out" }), () =>
    expect(page).toHaveURL(/\/login$/, { timeout: 2000 }),
  );

  await page.getByLabel("Work email").fill(email);
  await clickUntil(page.getByRole("button", { name: "Forgot password?" }), () =>
    expect(page.getByRole("dialog")).toBeVisible({ timeout: 1000 }),
  );
  await page.getByRole("button", { name: "Send reset link" }).click();
  await expect(page.getByText(`If an account exists for ${email}`)).toBeVisible();
  await expect(page.getByRole("button", { name: /Resend link in \d+s/ })).toBeDisabled();
  const resetLink = await latestLinkTo(email, "Reset");

  // The link works in another browser, once.
  const other = await browser.newPage();
  await other.goto(resetLink);
  await expect(other).toHaveURL(/\/reset-password$/);
  await other.getByLabel("New password").fill("second-password-2");
  await other.getByLabel("Confirm password").fill("second-password-2");
  await other.getByRole("button", { name: "Save password" }).click();
  await expect(other).toHaveURL(/\/workspaces$/);

  await page.goto(resetLink);
  await expect(
    page.getByRole("heading", { name: "This link has expired or was already used." }),
  ).toBeVisible();

  await page.goto("/login");
  await continueWithEmail(page, email, "second-password-2");
  await expect(page).toHaveURL(/\/workspaces$/);
});

import { expect, type Page, test } from "@playwright/test";

import { clickUntil } from "./hydration";
import { latestLinkTo } from "./mailpit";

async function continueWithEmail(page: Page, email: string, password: string) {
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Continue", exact: true }).click();
}

test("a new TA user signs up, verifies their email, logs out and signs back in", async ({
  page,
}) => {
  const email = `e2e-${Date.now()}@example.com`;
  const password = "correct-horse-battery";

  await page.goto("/login");
  await continueWithEmail(page, email, password);
  await expect(page).toHaveURL(/\/verify-email$/);
  await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible();

  // The verification link signs the user in; with no workspace yet they land on Choose workspace.
  await page.goto(await latestLinkTo(email));
  await expect(page).toHaveURL(/\/workspaces$/);

  await clickUntil(page.getByRole("button", { name: "Log out" }), () =>
    expect(page).toHaveURL(/\/login$/, { timeout: 2000 }),
  );

  await continueWithEmail(page, email, "not-the-password");
  await expect(page.getByText("That password doesn't match this email.")).toBeVisible();

  await continueWithEmail(page, email, password);
  await expect(page).toHaveURL(/\/workspaces$/);
});

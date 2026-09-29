import { expect, test } from "@playwright/test";

import { clickUntil } from "./hydration";
import { latestLinkTo } from "./mailpit";

test("an Admin invites a teammate, then resends and revokes the invite", async ({ page }) => {
  const stamp = `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
  const email = `e2e-invites-${stamp}@example.com`;
  const teammate = `teammate-${stamp}@example.com`;
  const name = `Invites ${Date.now()}`;
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
  await page.getByRole("button", { name: "Invite members" }).click();
  const dialog = page.getByRole("dialog", { name: "Invite a member" });
  await dialog.getByLabel(/Email address/).fill(email.toUpperCase());
  await dialog.getByRole("button", { name: "Send invite" }).click();
  await expect(dialog.getByText("This person already has access")).toBeVisible();

  await dialog.getByLabel(/Email address/).fill(teammate);
  await dialog.getByRole("button", { name: "Send invite" }).click();
  const share = page.getByRole("dialog", { name: "Invite ready" });
  const code = share.getByTestId("invite-code");
  await expect(code).toHaveText(/^[A-Z2-9]{4}-[A-Z2-9]{4}$/);
  const first = await code.textContent();
  await expect(share.getByRole("textbox")).toHaveValue(new RegExp(`${teammate}.*${first}`));
  await share.getByRole("button", { name: "Done" }).click();

  // Sending switches to the Pending invites tab.
  const tab = page.getByRole("tab", { name: /Pending invites/ });
  await expect(tab).toHaveAttribute("aria-selected", "true");
  await expect(page.getByText("1 pending invite")).toBeVisible();
  await expect(page.getByText(teammate)).toBeVisible();
  await expect(page.getByText("Invited as Recruiter · sent just now")).toBeVisible();
  await expect(page.getByText("Expires in 7 days")).toBeVisible();

  await page.getByRole("button", { name: `Resend the invite for ${teammate}` }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Reinvite" }).click();
  const resent = page.getByRole("dialog", { name: "Invite ready" }).getByTestId("invite-code");
  await expect(resent).toHaveText(/^[A-Z2-9]{4}-[A-Z2-9]{4}$/);
  expect(await resent.textContent()).not.toBe(first);
  await page.getByRole("button", { name: "Done" }).click();

  await page.getByRole("button", { name: `Revoke the invite for ${teammate}` }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Revoke invite" }).click();
  await expect(page.getByText("No pending invites.")).toBeVisible();
});

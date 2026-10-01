import { expect, type Page, test } from "@playwright/test";

import { clickUntil } from "./hydration";
import { latestLinkTo } from "./mailpit";

async function signUp(page: Page, email: string) {
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel("Password").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page).toHaveURL(/\/verify-email/);
  await page.goto(await latestLinkTo(email));
}

test("an invited teammate opens the link signed out, signs up and joins", async ({
  page,
  browser,
}) => {
  const stamp = `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
  const admin = `e2e-join-admin-${stamp}@example.com`;
  const teammate = `e2e-join-mate-${stamp}@example.com`;
  const name = `Join ${stamp}`;

  // An Admin creates a workspace and invites the teammate as a Recruiter.
  await page.goto("/login");
  await signUp(page, admin);
  const create = page.getByRole("button", { name: "Create workspace" });
  await clickUntil(create, () =>
    expect(page.getByText("Enter a name for your workspace.")).toBeVisible({ timeout: 2000 }),
  );
  await page.getByLabel("Workspace name").fill(name);
  await create.click();
  await expect(page.getByRole("heading", { name: `Welcome to ${name}` })).toBeVisible();
  await page.goto(new URL("/settings/members", page.url()).toString());
  await page.getByRole("button", { name: "Invite members" }).click();
  const dialog = page.getByRole("dialog", { name: "Invite a member" });
  await dialog.getByLabel(/Email address/).fill(teammate);
  await dialog.getByRole("button", { name: "Send invite" }).click();
  const code = await page.getByTestId("invite-code").textContent();
  expect(code).toMatch(/^[A-Z2-9]{4}-[A-Z2-9]{4}$/);

  // The Admin is the wrong account for this invite: only the masked email shows.
  await page.goto(`/join/${code}`);
  await expect(
    page.getByRole("heading", { name: "This invite is for another account" }),
  ).toBeVisible();
  await expect(page.getByText(`This invite was sent to e•••@example.com.`)).toBeVisible();
  await expect(page.getByText(name)).toHaveCount(0);

  // The teammate opens the link in a fresh browser, signs up, and lands back on the invite.
  const context = await browser.newContext();
  const invitee = await context.newPage();
  await invitee.goto(`/join/${code!.toLowerCase()}`);
  await expect(invitee).toHaveURL(/\/login\?next=/);
  await signUp(invitee, teammate);
  await expect(invitee).toHaveURL(new RegExp(`/join/${code!.toLowerCase()}$`));
  await expect(invitee.getByRole("heading", { name })).toBeVisible();
  await expect(invitee.getByText(`invited you to join ${name} as Recruiter.`)).toBeVisible();

  await invitee.getByRole("button", { name: `Join ${name}` }).click();
  await expect(invitee).toHaveURL(/app\.fasthyr\.localhost:\d+\/overview$/);

  // Opening the link again goes straight to the workspace.
  await invitee.goto(`/join/${code}`);
  await expect(invitee).toHaveURL(/app\.fasthyr\.localhost:\d+\/overview$/);
  await context.close();
});

test("an unknown invite link says so", async ({ page }) => {
  await page.goto("/login");
  await signUp(page, `e2e-join-none-${Date.now()}@example.com`);
  await expect(page).toHaveURL(/\/workspaces$/);
  await page.goto("/join/NOPE-0000");
  await expect(page.getByRole("heading", { name: "We couldn’t find that invite" })).toBeVisible();
  await page.getByRole("link", { name: "Go to your workspaces" }).click();
  await expect(page).toHaveURL(/\/workspaces$/);
});

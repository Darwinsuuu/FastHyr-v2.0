import { expect, type Page } from "@playwright/test";

import { clickUntil } from "./hydration";
import { latestLinkTo } from "./mailpit";

/** A new verified Admin with their own workspace, on the app's Getting started page. */
export async function signUpWithWorkspace(page: Page) {
  const email = `e2e-pipeline-${Date.now()}-${Math.random().toString(36).slice(2, 6)}@example.com`;
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
  await page.getByLabel("Workspace name").fill(`Pipelines ${Date.now()}`);
  await create.click();
  await expect(page.getByRole("heading", { name: /^Welcome to/ })).toBeVisible();
}

export async function addItems(page: Page, label: RegExp, items: string[]) {
  const input = page.getByLabel(label);
  for (const item of items) {
    await input.fill(item);
    await input.press("Enter");
  }
}

/** Publishes a remote pipeline that opens now with the trial's 20 credits, through the wizard,
 * and returns its ID. Starts on any app page of a new workspace. */
export async function publishPipeline(page: Page, title: string): Promise<string> {
  await page.goto(new URL("/pipelines/new", page.url()).toString());
  await expect(page.getByRole("heading", { name: "Tell us about the role" })).toBeVisible();
  await page.getByLabel("Job title").fill(title);
  await page.getByRole("radio", { name: "Remote" }).click();
  await page.getByLabel("Job description").fill("Lead our support team across chat and email.");
  await addItems(page, /Résumé must-haves/, ["Support experience", "Team leadership", "Zendesk"]);
  const continueButton = page.getByRole("button", { name: "Continue" });
  await clickUntil(continueButton, () =>
    expect(page.getByRole("heading", { name: "Shape the AI interview" })).toBeVisible({
      timeout: 2000,
    }),
  );
  await addItems(page, /Skills to probe/, ["De-escalation", "Coaching", "Metrics"]);
  await continueButton.click();
  await expect(page.getByRole("heading", { name: /Decide what a good interview/ })).toBeVisible();
  await continueButton.click();
  await expect(page.getByRole("heading", { name: "Set the schedule and credits" })).toBeVisible();
  await continueButton.click();
  await expect(page.getByRole("heading", { name: "Review and publish" })).toBeVisible();
  await page.getByRole("button", { name: "Publish pipeline" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel(/Type .I understand. to confirm/).fill("I understand");
  await dialog.getByRole("button", { name: "Publish pipeline" }).click();
  await expect(page.getByRole("heading", { name: `${title} is live` })).toBeVisible();
  const id = page.url().match(/pipelines\/([0-9a-f-]{36})/)?.[1];
  expect(id).toBeTruthy();
  return id as string;
}

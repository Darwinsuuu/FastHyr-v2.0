import { expect, type Page, test } from "@playwright/test";

import { clickUntil } from "./hydration";
import { latestLinkTo } from "./mailpit";

/** A new verified Admin with their own workspace, on the app's Getting started page. */
async function signUpWithWorkspace(page: Page) {
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

async function addItems(page: Page, label: RegExp, items: string[]) {
  const input = page.getByLabel(label);
  for (const item of items) {
    await input.fill(item);
    await input.press("Enter");
  }
}

test("the wizard needs 3 must-haves and 3 skills, and a saved draft reloads every field", async ({
  page,
}) => {
  await signUpWithWorkspace(page);
  await page
    .getByRole("navigation", { name: "Main" })
    .getByRole("link", { name: "Pipelines" })
    .click();
  await page.getByRole("link", { name: "New pipeline" }).click();
  await expect(page.getByRole("heading", { name: "Tell us about the role" })).toBeVisible();

  // Step 1: two must-haves aren't enough.
  await page.getByLabel("Job title").fill("Senior Backend Engineer");
  await page.getByLabel("Location").fill("Makati, Metro Manila");
  await page.getByLabel("Job description").fill("Build and run our payments platform.");
  await addItems(page, /Résumé must-haves/, ["5+ years backend development", "PostgreSQL"]);
  const continueButton = page.getByRole("button", { name: "Continue" });
  await clickUntil(continueButton, () =>
    expect(page.locator("#main").getByRole("alert")).toHaveText(
      "Add at least 3 must-haves to continue",
      {
        timeout: 2000,
      },
    ),
  );
  await expect(page.getByRole("heading", { name: "Tell us about the role" })).toBeVisible();

  await addItems(page, /Résumé must-haves/, ["Distributed systems"]);
  await addItems(page, /Nice-to-haves/, ["Kubernetes"]);
  await page.getByRole("radio", { name: "Remote" }).click();
  await page.getByRole("checkbox", { name: /Career changers/ }).click();
  await expect(page.getByText(/We won.t screen out career changers/)).toBeVisible();
  await continueButton.click();

  // Step 2: the same rule for skills to probe.
  await expect(page.getByRole("heading", { name: "Shape the AI interview" })).toBeVisible();
  await expect(page).toHaveURL(/\/pipelines\/[0-9a-f-]{36}\/edit$/);
  await page.getByRole("radio", { name: /Voice only/ }).click();
  await page.getByRole("radio", { name: /Direct/ }).click();
  await page.getByRole("radio", { name: "Senior" }).click();
  await addItems(page, /Skills to probe/, ["System design", "API design"]);
  await continueButton.click();
  await expect(page.locator("#main").getByRole("alert")).toHaveText(
    "Add at least 3 skills to probe to continue",
  );
  await addItems(page, /Skills to probe/, ["Code review"]);
  await page.getByRole("switch", { name: /Remind candidates/ }).click();
  await continueButton.click();
  await expect(page.getByRole("heading", { name: /Decide what a good interview/ })).toBeVisible();

  // Reload the draft: every field comes back.
  await page.reload();
  await expect(page.getByLabel("Job title")).toHaveValue("Senior Backend Engineer");
  await expect(page.getByLabel("Location")).toHaveValue("Makati, Metro Manila");
  await expect(page.getByLabel("Job description")).toHaveValue(
    "Build and run our payments platform.",
  );
  for (const item of ["5+ years backend development", "PostgreSQL", "Distributed systems"]) {
    await expect(page.getByRole("button", { name: `Remove ${item}` })).toBeVisible();
  }
  await expect(page.getByRole("button", { name: "Remove Kubernetes" })).toBeVisible();
  await expect(page.getByRole("radio", { name: "Remote" })).toHaveAttribute("aria-checked", "true");
  await expect(page.getByRole("checkbox", { name: /Career changers/ })).toBeChecked();

  await clickUntil(continueButton, () =>
    expect(page.getByRole("heading", { name: "Shape the AI interview" })).toBeVisible({
      timeout: 2000,
    }),
  );
  await expect(page.getByRole("radio", { name: /Voice only/ })).toHaveAttribute(
    "aria-checked",
    "true",
  );
  await expect(page.getByRole("radio", { name: /Direct/ })).toHaveAttribute("aria-checked", "true");
  await expect(page.getByRole("radio", { name: "Senior" })).toHaveAttribute("aria-checked", "true");
  for (const item of ["System design", "API design", "Code review"]) {
    await expect(page.getByRole("button", { name: `Remove ${item}` })).toBeVisible();
  }
  await expect(page.getByRole("switch", { name: /Remind candidates/ })).not.toBeChecked();
  await expect(page.getByRole("switch", { name: /Flag possible impersonation/ })).toBeChecked();
});

test("a pipeline is published with its weights adding up to 100 and a reserve within the free credits", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await signUpWithWorkspace(page);
  await page.goto(new URL("/pipelines/new", page.url()).toString());
  await expect(page.getByRole("heading", { name: "Tell us about the role" })).toBeVisible();

  await page.getByLabel("Job title").fill("Support Team Lead");
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

  // Step 3: the rubric must add up to 100.
  await expect(page.getByRole("heading", { name: /Decide what a good interview/ })).toBeVisible();
  const technical = page.getByRole("slider", { name: "Technical fit" });
  await technical.focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByText("Adds up to 105%. Needs to be 100%")).toBeVisible();
  await continueButton.click();
  await expect(page.getByText("Make the rubric add up to 100% to continue")).toBeVisible();
  await expect(page.getByRole("heading", { name: /Decide what a good interview/ })).toBeVisible();
  await technical.focus();
  await page.keyboard.press("ArrowLeft");
  await continueButton.click();

  // Step 4: a new workspace has its 20 trial credits free, so 30 is too many.
  await expect(page.getByRole("heading", { name: "Set the schedule and credits" })).toBeVisible();
  const reserve = page.getByLabel("Credits to reserve");
  await expect(reserve).toHaveValue("20");
  await page.getByRole("button", { name: "Add 10 credits" }).click();
  await expect(
    page.getByText(/That's more than the 20 credits your workspace has free/),
  ).toBeVisible();
  await continueButton.click();

  // Review: publish is blocked until the reserve fits.
  await expect(page.getByRole("heading", { name: "Review and publish" })).toBeVisible();
  const publishButton = page.getByRole("button", { name: "Publish pipeline" });
  await publishButton.click();
  await expect(
    page.getByText("Reserve no more credits than your workspace has free to publish"),
  ).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("button", { name: "Edit Schedule & credits" }).click();
  await page.getByRole("button", { name: "Remove 10 credits" }).click();
  await expect(reserve).toHaveValue("20");
  await continueButton.click();

  // Publishing needs "I understand".
  await publishButton.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("heading", { name: /there's no going back/ })).toBeVisible();
  const confirm = dialog.getByRole("button", { name: "Publish pipeline" });
  await expect(confirm).toBeDisabled();
  await dialog.getByLabel(/Type .I understand. to confirm/).fill("I understand");
  await confirm.click();

  await expect(page.getByRole("heading", { name: "Support Team Lead is live" })).toBeVisible();
  await page.getByRole("button", { name: "Copy apply link for LinkedIn" }).click();
  await expect(page.getByText(/turn off Easy Apply/)).toBeVisible();
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  expect(copied).toMatch(/\/apply\/[a-z0-9-]+\/support-team-lead\?source=linkedin$/);

  // The copied link opens the public apply page (APPLY-001) without the hidden criteria.
  const applyPage = await context.newPage();
  await applyPage.goto(copied);
  await expect(
    applyPage.getByRole("heading", { level: 1, name: "Support Team Lead" }),
  ).toBeVisible();
  await expect(applyPage.getByText(/^Accepting applications · closes /)).toBeVisible();
  await expect(applyPage.getByText("Lead our support team across chat and email.")).toBeVisible();
  await expect(applyPage.getByText("Zendesk")).toHaveCount(0);
  await expect(applyPage.getByText("De-escalation")).toHaveCount(0);
  await expect(applyPage.getByRole("button", { name: "Apply now" }).first()).toBeEnabled();
  await expect
    .poll(() => applyPage.evaluate(() => Object.values({ ...sessionStorage })))
    .toContain("linkedin");
  await applyPage.close();

  // The live pipeline's setup is locked.
  const pipelineId = page.url().match(/pipelines\/([0-9a-f-]{36})/)?.[1];
  await page.goto(new URL(`/pipelines/${pipelineId}/edit`, page.url()).toString());
  await expect(
    page.getByRole("heading", { name: "This pipeline's setup is locked" }),
  ).toBeVisible();
});

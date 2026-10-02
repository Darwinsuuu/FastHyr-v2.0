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

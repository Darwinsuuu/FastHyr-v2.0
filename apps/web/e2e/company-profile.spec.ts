import { expect, type Page, test } from "@playwright/test";
import path from "node:path";

import { clickUntil } from "./hydration";
import { latestLinkTo } from "./mailpit";

/** A new verified Admin with their own workspace. */
async function signUpWithWorkspace(page: Page) {
  const email = `e2e-company-${Date.now()}-${Math.random().toString(36).slice(2, 6)}@example.com`;
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
  await page.getByLabel("Workspace name").fill(`Company ${Date.now()}`);
  await create.click();
  await expect(page.getByRole("heading", { name: /^Welcome to/ })).toBeVisible();
}

test("an Admin saves the company profile with an SVG logo", async ({ page }) => {
  await signUpWithWorkspace(page);
  await page
    .getByRole("navigation", { name: "Main" })
    .getByRole("link", { name: "Company profile" })
    .click();
  await expect(page.getByRole("heading", { name: "Company profile" })).toBeVisible();

  await page.getByLabel("Company name").fill("Northwind Hiring");
  await page.getByLabel("Website").fill("not a url");
  await page.getByLabel("About your company").fill("We hire with care.");
  await expect(page.getByText("18 / 600")).toBeVisible();
  await page
    .getByLabel("Upload a logo")
    .setInputFiles(path.join(__dirname, "fixtures", "logo.svg"));
  await expect(page.getByRole("img", { name: "Your company logo" })).toBeVisible();

  const save = page.getByRole("button", { name: "Save changes" }).first();
  await save.click();
  await expect(page.getByText("Enter a web address like yourcompany.com.")).toBeVisible();
  await page.getByLabel("Website").fill("northwind.example.com");
  await save.click();
  await expect(page.getByText("Company profile saved")).toBeVisible();

  await page.reload();
  await expect(page.getByLabel("Company name")).toHaveValue("Northwind Hiring");
  await expect(page.getByLabel("Website")).toHaveValue("northwind.example.com");
  await expect(page.getByLabel("About your company")).toHaveValue("We hire with care.");
  await expect(page.getByRole("img", { name: "Your company logo" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Remove logo" })).toBeVisible();
});

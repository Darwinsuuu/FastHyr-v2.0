import { expect, test } from "@playwright/test";

import { signUpWithWorkspace } from "./pipelines";

test("an Admin edits, resets, restores and tests a rejection email", async ({ page }) => {
  await signUpWithWorkspace(page);
  await page
    .getByRole("navigation", { name: "Main" })
    .getByRole("link", { name: "Email templates" })
    .click();
  await expect(page.getByRole("heading", { name: "Email templates", level: 1 })).toBeVisible();
  await page.getByRole("button", { name: /^Rejections/ }).click();
  await expect(page.getByRole("article")).toHaveCount(2);
  await page.getByRole("link", { name: "Edit Not moving forward — résumé" }).click();

  await expect(page.getByRole("heading", { name: "Not moving forward — résumé" })).toBeVisible();
  // Rejections always end with the locked review line, and the history starts empty.
  await expect(page.getByText("This line is always included")).toBeVisible();
  await expect(page.getByText("No changes yet.")).toBeVisible();

  const subject = page.getByLabel("Subject line");
  await subject.fill("About your [Job.title] application [Interview.link]");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("[Interview.link] can’t be used in this email.")).toBeVisible();

  await subject.fill("About your [Job.title] application, ");
  const message = page.getByRole("textbox", { name: "Message" });
  await message.click();
  await page.keyboard.press("Control+End");
  await page.keyboard.press("Enter");
  await page.keyboard.type("Thanks again, ");
  await page.getByRole("button", { name: /\[Candidate\.firstname\]/ }).click();
  await expect(message.locator("[data-parameter]").last()).toHaveText("[Candidate.firstname]");

  await page.getByRole("button", { name: "Send test to me" }).click();
  const test = page.getByRole("dialog");
  await expect(test.getByText("About your Senior Backend Engineer application,")).toBeVisible();
  await test.getByRole("button", { name: "Send test" }).click();
  await expect(test.getByRole("heading", { name: "Test email sent" })).toBeVisible();
  await test.getByRole("button", { name: "Done" }).click();

  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page).toHaveURL(/\/settings\/email-templates$/);
  const card = page.getByRole("article").filter({ hasText: "Not moving forward — résumé" });
  await expect(card).toContainText("Edited ");

  await card.getByRole("link", { name: /Edit/ }).click();
  await expect(subject).toHaveValue("About your [Job.title] application,");
  await page.getByRole("button", { name: "Reset to default" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Reset to default" }).click();
  await expect(subject).toHaveValue("An update on your application");

  // Bring the edit back from the history: a new version on top.
  await page.getByRole("button", { name: /edited the template/ }).click();
  await expect(page.getByText(/You’re viewing the version from/)).toBeVisible();
  await page.getByRole("button", { name: "Restore this version" }).click();
  await expect(subject).toHaveValue("About your [Job.title] application,");
  await expect(page.getByRole("button", { name: /restored an earlier version/ })).toBeVisible();
});

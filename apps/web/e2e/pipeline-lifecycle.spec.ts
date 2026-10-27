import { expect, test } from "@playwright/test";

import { publishPipeline, signUpWithWorkspace } from "./pipelines";

// PIPE-005: pause, resume, close, duplicate and archive from the Pipelines list and the
// pipeline's own header.
test("a pipeline is paused, resumed, closed, duplicated and archived", async ({ page }) => {
  await signUpWithWorkspace(page);
  const id = await publishPipeline(page, "Support Team Lead");
  const title = "Support Team Lead";
  const actions = `Actions for ${title}`;
  const toast = (text: string) =>
    expect(page.getByRole("status").filter({ hasText: text }).first()).toBeVisible();

  await page.goto(new URL("/pipelines", page.url()).toString());
  const row = page.getByRole("row", { name: new RegExp(title) });
  await expect(row).toContainText("Live");

  // Pause asks first and says the countdown keeps going.
  await row.getByRole("button", { name: actions }).click();
  await page.getByRole("menuitem", { name: "Pause pipeline" }).click();
  const pause = page.getByRole("dialog", { name: `Pause ${title}?` });
  await expect(pause.getByText("The countdown doesn't stop.")).toBeVisible();
  await pause.getByRole("button", { name: "Pause pipeline" }).click();
  await toast(`${title} is paused`);
  await expect(row).toContainText("Paused");

  // Resume runs at once.
  await row.getByRole("button", { name: actions }).click();
  await page.getByRole("menuitem", { name: "Resume pipeline" }).click();
  await toast(`${title} is live again`);
  await expect(row).toContainText("Live");

  // Close from the pipeline's header, with the Role closed email ticked (nobody applied yet).
  await page.goto(new URL(`/pipelines/${id}`, page.url()).toString());
  await page.getByRole("button", { name: "More actions" }).click();
  await page.getByRole("menuitem", { name: "Close pipeline" }).click();
  const close = page.getByRole("dialog", { name: `Close ${title}?` });
  await expect(close.getByRole("checkbox", { name: /Let candidates who haven't/ })).toBeChecked();
  await close.getByRole("button", { name: "Close pipeline" }).click();
  await toast(`${title} is closed`);

  // Duplicate makes a new draft and opens its wizard with the same setup.
  await page.getByRole("button", { name: "More actions" }).click();
  await page.getByRole("menuitem", { name: "Duplicate as new pipeline" }).click();
  await expect(page).toHaveURL(/\/pipelines\/[0-9a-f-]{36}\/edit$/);
  await expect(page).not.toHaveURL(new RegExp(id));
  await expect(page.getByLabel("Job title")).toHaveValue(title);

  // Archive moves the closed one out of the list.
  await page.goto(new URL("/pipelines", page.url()).toString());
  await page.getByRole("radio", { name: /^Closed/ }).click();
  await row.getByRole("button", { name: actions }).click();
  await page.getByRole("menuitem", { name: "Archive" }).click();
  await page
    .getByRole("dialog", { name: `Archive ${title}?` })
    .getByRole("button", { name: "Archive pipeline" })
    .click();
  await toast(`${title} is archived`);
  await expect(page.getByRole("radio", { name: /^Closed/ })).toContainText("0");
});

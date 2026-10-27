import { expect, test } from "@playwright/test";

import { publishPipeline, signUpWithWorkspace } from "./pipelines";

// PIPE-006: Copy apply link in the Pipelines list and Share apply link on the pipeline's header
// open the share modal; a tile copies the apply link tagged with its source.
test("the share modal copies an apply link tagged with its source", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await signUpWithWorkspace(page);
  const title = "Support Team Lead";
  const id = await publishPipeline(page, title);
  const copied = () => page.evaluate(() => navigator.clipboard.readText());

  await page.goto(new URL("/pipelines", page.url()).toString());
  const row = page.getByRole("row", { name: new RegExp(title) });
  await row.getByRole("button", { name: `Actions for ${title}` }).click();
  await page.getByRole("menuitem", { name: "Copy apply link" }).click();
  const share = page.getByRole("dialog", { name: `Where will you post ${title}?` });
  await share.getByRole("button", { name: "Copy apply link for LinkedIn" }).click();
  await expect(share.getByText("turn off Easy Apply")).toBeVisible();
  expect(await copied()).toMatch(/\/apply\/[a-z0-9-]+\/support-team-lead\?source=linkedin$/);
  await share.getByRole("button", { name: "Close" }).click();
  await expect(share).toBeHidden();

  await page.goto(new URL(`/pipelines/${id}`, page.url()).toString());
  await page.getByRole("button", { name: "Share apply link" }).click();
  await share.getByRole("button", { name: "Copy apply link for Other" }).click();
  expect(await copied()).toMatch(/\/support-team-lead\?source=other$/);
});

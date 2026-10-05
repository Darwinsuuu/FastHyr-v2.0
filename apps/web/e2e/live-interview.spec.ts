import { expect, test } from "@playwright/test";

// The live interview stage (INTV-005) on the dev preview page: Chromium's fake camera and
// microphone, the scripted stand-in for OpenAI Realtime, and a fake API.
test.use({
  permissions: ["camera", "microphone"],
  launchOptions: {
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH || undefined,
    args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
  },
});

test("the interviewer speaks with captions, topics move, mute pauses the mic, and End asks first", async ({
  page,
}) => {
  await page.goto("/dev/interview");
  await expect(page.getByRole("timer", { name: "Time remaining in this interview" })).toContainText(
    /2\d:\d\d/,
  );
  await expect(page.getByLabel("Your camera").first()).toBeAttached();

  const captions = page.getByRole("log", { name: "Conversation transcript" });
  await expect(captions).toContainText("Ready to start?");
  await expect(captions).toContainText("Yes, ready. Thanks for having me.");
  await expect(page.getByRole("listitem").filter({ hasText: "Warm-up" })).toHaveAttribute(
    "aria-current",
    "step",
  );

  const mute = page.getByRole("button", { name: "Mute" });
  await mute.click();
  await expect(page.getByRole("button", { name: "Unmute" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.getByText("Paused — your mic is off")).toBeVisible();
  await page.getByRole("button", { name: "Unmute" }).click();

  await expect(page.getByText("From your résumé:")).toBeVisible({ timeout: 20_000 });
  await expect(
    page.getByRole("listitem").filter({ hasText: "Platform migration" }),
  ).toHaveAttribute("aria-current", "step");

  await page.getByRole("button", { name: "End interview" }).click();
  const dialog = page.getByRole("dialog", { name: "End the interview now?" });
  await dialog.getByRole("button", { name: "Keep talking" }).click();
  await expect(dialog).toBeHidden();
  await page.getByRole("button", { name: "End interview" }).click();
  await dialog.getByRole("button", { name: "End interview" }).click();
  await expect(page.getByRole("heading", { name: "Session ended" })).toBeVisible();
});

test("a voice-only interview shows the mic, not the camera", async ({ page }) => {
  await page.goto("/dev/interview?format=voice&time=100");
  await expect(page.getByText("You · mic on")).toBeVisible();
  await expect(page.getByLabel("Your camera")).toHaveCount(0);
  // The last 2 minutes.
  await expect(page.getByRole("timer")).toContainText(/1:\d\d/);
});

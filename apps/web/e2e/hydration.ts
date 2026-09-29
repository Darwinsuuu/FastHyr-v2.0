import { expect, type Locator } from "@playwright/test";

/**
 * Clicks until `settled` passes. In `next dev` a page can show before React hydrates it, and a
 * click in that moment does nothing.
 */
export async function clickUntil(button: Locator, settled: () => Promise<void>): Promise<void> {
  await expect(async () => {
    await button.click();
    await settled();
  }).toPass();
}

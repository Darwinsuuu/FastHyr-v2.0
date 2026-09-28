import { defineConfig, devices } from "@playwright/test";

// End-to-end tests run against the local stack: start it with `make dev` first, then `make e2e`.
// Emails are read from local Supabase's Mailpit.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: process.env.E2E_SITE_URL ?? "http://fasthyr.localhost:3000",
    trace: "retain-on-failure",
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH || undefined },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});

import { defineConfig, devices } from "@playwright/test";

const WEB_PORT = 5173;
const WEB_URL = `http://127.0.0.1:${WEB_PORT}`;

export default defineConfig({
  testDir: ".",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "list",
  use: {
    baseURL: WEB_URL,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "pnpm --filter web dev",
    url: WEB_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    cwd: "../../",
  },
});

import { defineConfig, devices } from "@playwright/test";
import { API_PORT, MONGO_URL, WEB_PORT } from "./tests/e2e/environment";

const CI = process.env.CI !== undefined;

export default defineConfig({
  testDir: "tests/e2e",
  // Every test empties and seeds the same database.
  workers: 1,
  forbidOnly: CI,
  reporter: CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: { baseURL: `http://localhost:${WEB_PORT}`, trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "uv run --project .. daily-trends-py",
      url: `http://localhost:${API_PORT}/status`,
      // The startup scrape would read the real newspapers.
      env: { ENV: "test", PORT: API_PORT, MONGO_URL, SCRAPE_SCHEDULE_ENABLED: "false" },
      timeout: 60_000,
    },
    {
      command: `vite build && vite preview --port ${WEB_PORT} --strictPort`,
      url: `http://localhost:${WEB_PORT}`,
      env: { API_PORT },
      timeout: 120_000,
    },
  ],
});

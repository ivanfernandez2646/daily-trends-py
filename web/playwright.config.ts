import { defineConfig, devices } from "@playwright/test";
import {
  API_PORT,
  EXPIRY_API_PORT,
  EXPIRY_TOKEN_TTL_SECONDS,
  EXPIRY_WEB_PORT,
  MONGO_URL,
  WEB_PORT,
} from "./tests/e2e/environment";

const CI = process.env.CI !== undefined;

// The startup scrape would read the real newspapers.
const API_ENV = { ENV: "test", MONGO_URL, SCRAPE_SCHEDULE_ENABLED: "false" };

export default defineConfig({
  testDir: "tests/e2e",
  // Every test empties and seeds the same database.
  workers: 1,
  forbidOnly: CI,
  reporter: CI ? [["list"], ["html", { open: "never" }]] : "list",
  globalSetup: "./tests/e2e/global-setup.ts",
  use: { trace: "retain-on-failure" },
  projects: [
    {
      name: "chromium",
      testIgnore: "*.expiry.spec.ts",
      use: { ...devices["Desktop Chrome"], baseURL: `http://localhost:${WEB_PORT}` },
    },
    {
      name: "session-expiry",
      testMatch: "*.expiry.spec.ts",
      use: { ...devices["Desktop Chrome"], baseURL: `http://localhost:${EXPIRY_WEB_PORT}` },
    },
  ],
  // Started in order, so the second app serves the build of the first.
  webServer: [
    {
      command: "uv run --project .. daily-trends-py",
      url: `http://localhost:${API_PORT}/status`,
      env: { ...API_ENV, PORT: API_PORT },
      timeout: 60_000,
    },
    {
      command: `vite build && vite preview --port ${WEB_PORT} --strictPort`,
      url: `http://localhost:${WEB_PORT}`,
      env: { API_PORT },
      timeout: 120_000,
    },
    {
      command: "uv run --project .. daily-trends-py",
      url: `http://localhost:${EXPIRY_API_PORT}/status`,
      env: {
        ...API_ENV,
        PORT: EXPIRY_API_PORT,
        AUTH_TOKEN_TTL_SECONDS: String(EXPIRY_TOKEN_TTL_SECONDS),
      },
      timeout: 60_000,
    },
    {
      command: `vite preview --port ${EXPIRY_WEB_PORT} --strictPort`,
      url: `http://localhost:${EXPIRY_WEB_PORT}`,
      env: { API_PORT: EXPIRY_API_PORT },
      timeout: 60_000,
    },
  ],
});

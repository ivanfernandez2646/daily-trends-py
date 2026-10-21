import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

// Anchored: a prefix such as `/feed` would also catch the app's own `/feeds` pages.
const API_PATHS = ["^/feed/", "^/auth/", "^/status$"];

export default defineConfig(({ mode }) => {
  // The API reads its port from the repository's `.env`; `API_PORT` points the app elsewhere.
  const rootEnv = loadEnv(mode, "..", "");
  const apiPort = process.env.API_PORT ?? rootEnv.PORT ?? "5000";
  const proxy = Object.fromEntries(API_PATHS.map((path) => [path, `http://localhost:${apiPort}`]));

  return {
    plugins: [
      tanstackRouter({
        target: "react",
        autoCodeSplitting: true,
        routeFileIgnorePattern: "\\.test\\.",
      }),
      react(),
      tailwindcss(),
    ],
    // `vite preview` uses the same proxy.
    server: { port: 5173, strictPort: true, proxy },
    test: {
      environment: "jsdom",
      include: ["src/**/*.test.{ts,tsx}"],
      setupFiles: ["src/test/setup.ts"],
    },
  };
});

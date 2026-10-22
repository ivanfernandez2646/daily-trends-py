import { describe, expect, it } from "vitest";
import { safeRedirect } from "./redirect";

describe("safeRedirect", () => {
  it.each([
    "/admin",
    "/admin/feeds/6b1c7f8e-1d2e-4f3a-9b8c-7d6e5f4a3b2c/edit",
    "/admin?q=madrid&category=SPORTS",
    "/feeds#buscar",
  ])("keeps a path of the app: %s", (path) => {
    expect(safeRedirect(path)).toBe(path);
  });

  it.each([
    ["another site", "https://evil.example"],
    ["a protocol-relative address", "//evil.example"],
    ["a backslash that browsers read as a slash", "/\\evil.example"],
    ["a relative path", "admin"],
    ["a script", "javascript:alert(1)"],
    ["an empty value", ""],
    ["no value", undefined],
    ["a value that is not text", 42],
  ])("sends %s to /admin", (_name, value) => {
    expect(safeRedirect(value)).toBe("/admin");
  });
});

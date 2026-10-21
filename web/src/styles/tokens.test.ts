import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// Read from disk: Vitest does not process CSS imports.
const tokensCss = readFileSync(join(import.meta.dirname, "tokens.css"), "utf8");

type Theme = Map<string, string>;

function declarations(block: string): Theme {
  return new Map(
    [...block.matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)].map(([, name = "", value = ""]) => [
      name,
      value,
    ]),
  );
}

function themes(css: string): { light: Theme; dark: Theme } {
  const darkStart = css.indexOf("@media (prefers-color-scheme: dark)");
  return { light: declarations(css.slice(0, darkStart)), dark: declarations(css.slice(darkStart)) };
}

function luminance(hex: string): number {
  const [r = 0, g = 0, b = 0] = [1, 3, 5]
    .map((start) => Number.parseInt(hex.slice(start, start + 2), 16) / 255)
    .map((channel) => (channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(foreground: string, background: string): number {
  const [lighter = 0, darker = 0] = [luminance(foreground), luminance(background)].sort(
    (a, b) => b - a,
  );
  return (lighter + 0.05) / (darker + 0.05);
}

const TEXT_ON_BACKGROUNDS = ["ink", "ink-soft", "meta", "accent", "error-fg"].flatMap((text) =>
  ["paper", "surface", "canvas"].map((background) => [text, background] as const),
);
const PAIRS = [
  ...TEXT_ON_BACKGROUNDS,
  ["danger", "surface"],
  ["surface", "ink"],
  ["surface", "danger"],
  ["success-fg", "success-bg"],
  ["error-fg", "error-bg"],
] as const;

describe.each(Object.entries(themes(tokensCss)))("the %s theme", (_name, theme) => {
  it.each(PAIRS)("%s on %s passes WCAG AA", (text, background) => {
    const foreground = theme.get(text);
    const back = theme.get(background);
    expect(foreground, text).toBeDefined();
    expect(back, background).toBeDefined();

    expect(contrast(foreground ?? "", back ?? "")).toBeGreaterThanOrEqual(4.5);
  });
});

it("defines the same tokens in both themes", () => {
  const { light, dark } = themes(tokensCss);

  expect([...dark.keys()].sort()).toEqual([...light.keys()].sort());
  expect(light.size).toBeGreaterThan(0);
});

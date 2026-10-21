import { expect, it } from "vitest";
import { cn } from "./utils";

it("keeps a Tinta type size next to a text color", () => {
  expect(cn("text-display", "text-ink")).toBe("text-display text-ink");
});

it("lets a later type size win", () => {
  expect(cn("text-title-2", "text-display")).toBe("text-display");
});

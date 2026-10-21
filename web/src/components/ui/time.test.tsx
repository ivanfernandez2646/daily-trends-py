import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { Time } from "./time";

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-21T10:00:00Z"));
});

afterEach(() => {
  vi.useRealTimers();
});

it("shows a relative time and keeps the exact instant", () => {
  render(<Time iso="2026-10-21T08:00:00Z" />);

  const time = screen.getByText("hace 2 h");
  expect(time.tagName).toBe("TIME");
  expect(time).toHaveAttribute("datetime", "2026-10-21T08:00:00Z");
  expect(time).toHaveAttribute("title", "21 de octubre de 2026 a las 10:00");
});

it("shows the full date when asked", () => {
  render(<Time iso="2026-10-21T08:00:00Z" format="full" />);

  expect(screen.getByText("21 de octubre de 2026 a las 10:00").tagName).toBe("TIME");
});

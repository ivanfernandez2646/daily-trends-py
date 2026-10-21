import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useDebouncedValue } from "./use-debounced-value";

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

it("changes once the value stops changing for the delay", () => {
  const { result, rerender } = renderHook(({ value }) => useDebouncedValue(value, 300), {
    initialProps: { value: "m" },
  });

  rerender({ value: "ma" });
  act(() => vi.advanceTimersByTime(200));
  rerender({ value: "mad" });
  act(() => vi.advanceTimersByTime(299));

  expect(result.current).toBe("m");

  act(() => vi.advanceTimersByTime(1));

  expect(result.current).toBe("mad");
});

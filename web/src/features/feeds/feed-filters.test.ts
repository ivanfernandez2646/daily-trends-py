import { expect, it } from "vitest";
import { parseFeedFilters } from "./feed-filters";

it("keeps valid filters", () => {
  expect(parseFeedFilters({ category: "SPORTS", source: "EL_PAIS", q: "madrid" })).toEqual({
    category: "SPORTS",
    source: "EL_PAIS",
    q: "madrid",
  });
});

it("has no filters by default", () => {
  expect(parseFeedFilters({})).toEqual({});
});

it.each([
  [{ category: "nope" }],
  [{ category: "sports" }],
  [{ source: "ABC" }],
  [{ category: 3 }],
  [{ q: "   " }],
  [{ q: "a".repeat(101) }],
  [{ q: ["madrid"] }],
])("drops an invalid value: %j", (search) => {
  expect(parseFeedFilters(search)).toEqual({});
});

it("trims the search", () => {
  expect(parseFeedFilters({ q: "  madrid  " })).toEqual({ q: "madrid" });
});

it("keeps a search of 100 characters", () => {
  const q = "a".repeat(100);

  expect(parseFeedFilters({ q })).toEqual({ q });
});

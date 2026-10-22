import type { FeedFilters } from "../../api/types";
import { categoryLabel, isCategory, isSource, sourceLabel } from "../../lib/labels";

const MAX_SEARCH_LENGTH = 100;

/** The filters of the browse URL: a value the API would reject is dropped, never sent. */
export function parseFeedFilters(search: Record<string, unknown>): FeedFilters {
  const { category, source, q } = search;
  const text = typeof q === "string" ? q.trim() : "";
  return {
    ...(typeof category === "string" && isCategory(category) && { category }),
    ...(typeof source === "string" && isSource(source) && { source }),
    ...(text !== "" && text.length <= MAX_SEARCH_LENGTH && { q: text }),
  };
}

/**
 * The filters to rewrite a URL to, when any of its raw search params is invalid, unknown or not
 * as the page would write it; `undefined` when the URL is already right.
 */
export function filtersToRewrite(search: Record<string, unknown>): FeedFilters | undefined {
  const filters = parseFeedFilters(search);
  const kept = Object.entries(search).every(
    ([key, value]) => filters[key as keyof FeedFilters] === value,
  );
  return kept ? undefined : filters;
}

/** The filters with `change` applied; a filter set to `undefined` is removed. */
export function updateFilters(filters: FeedFilters, change: Partial<FeedFilters>): FeedFilters {
  const next = { ...filters, ...change };
  return Object.fromEntries(
    Object.entries(next).filter(([, value]) => value !== undefined),
  ) as FeedFilters;
}

export function countFilters(filters: FeedFilters): number {
  return Object.values(filters).filter((value) => value !== undefined).length;
}

/** *con “madrid” en Deportes de El Mundo*: the active filters, as words. */
export function describeFilters({ category, source, q }: FeedFilters): string {
  return [
    q !== undefined && `con “${q}”`,
    category !== undefined && `en ${categoryLabel(category)}`,
    source !== undefined && `de ${sourceLabel(source)}`,
  ]
    .filter(Boolean)
    .join(" ");
}

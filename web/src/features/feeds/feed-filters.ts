import type { FeedCategory, FeedSource } from "../../api/types";
import { isCategory, isSource } from "../../lib/labels";

export type FeedFilters = { category?: FeedCategory; source?: FeedSource; q?: string };

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

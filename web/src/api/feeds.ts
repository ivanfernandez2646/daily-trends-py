import {
  infiniteQueryOptions,
  queryOptions,
  skipToken,
  useInfiniteQuery,
  useQuery,
} from "@tanstack/react-query";
import { api, unwrap } from "./client";
import type { FeedCategory, FeedFilters } from "./types";

const PAGE_SIZE = 20;

export const feedKeys = {
  all: ["feeds"] as const,
  home: () => [...feedKeys.all, "home"] as const,
  list: (filters: FeedFilters) => [...feedKeys.all, "list", filters] as const,
  detail: (id: string) => [...feedKeys.all, "detail", id] as const,
  related: (category: FeedCategory) => [...feedKeys.all, "related", category] as const,
};

const RELATED_COUNT = 3;

export const homeFeedsQuery = queryOptions({
  queryKey: feedKeys.home(),
  queryFn: () => unwrap(api.GET("/feed/home")),
});

export function useHomeFeeds() {
  return useQuery(homeFeedsQuery);
}

/** Pages of the feeds that match `filters`, newest first; each set of filters is its own list. */
export function feedListQuery(filters: FeedFilters) {
  return infiniteQueryOptions({
    queryKey: feedKeys.list(filters),
    queryFn: ({ pageParam, signal }) =>
      unwrap(
        api.GET("/feed/list", {
          params: {
            query: {
              limit: PAGE_SIZE,
              ...filters,
              ...(pageParam !== undefined && { cursor: pageParam }),
            },
          },
          signal,
        }),
      ),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
}

export function useFeedList(filters: FeedFilters) {
  return useInfiniteQuery(feedListQuery(filters));
}

export function feedQuery(id: string) {
  return queryOptions({
    queryKey: feedKeys.detail(id),
    queryFn: () => unwrap(api.GET("/feed/{id}", { params: { path: { id } } })),
  });
}

export function useFeed(id: string) {
  return useQuery(feedQuery(id));
}

/** Up to three other feeds of `category`, newest first, once the category is known. */
export function useRelatedFeeds(category: FeedCategory | undefined, excludeId: string) {
  return useQuery({
    queryKey: category === undefined ? [...feedKeys.all, "related"] : feedKeys.related(category),
    // One more than shown, in case the feed itself is among them.
    queryFn:
      category === undefined
        ? skipToken
        : () =>
            unwrap(
              api.GET("/feed/list", {
                params: { query: { category, limit: RELATED_COUNT + 1 } },
              }),
            ),
    select: (page) => page.items.filter((feed) => feed.id !== excludeId).slice(0, RELATED_COUNT),
  });
}

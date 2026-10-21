import {
  infiniteQueryOptions,
  queryOptions,
  useInfiniteQuery,
  useQuery,
} from "@tanstack/react-query";
import { api, unwrap } from "./client";
import type { FeedFilters } from "./types";

const PAGE_SIZE = 20;

export const feedKeys = {
  all: ["feeds"] as const,
  home: () => [...feedKeys.all, "home"] as const,
  list: (filters: FeedFilters) => [...feedKeys.all, "list", filters] as const,
};

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

import {
  type InfiniteData,
  infiniteQueryOptions,
  queryOptions,
  skipToken,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { ApiError, api, unwrap, unwrapEmpty } from "./client";
import type {
  CreateFeedRequest,
  FeedCategory,
  FeedFilters,
  FeedPageResponse,
  UpdateFeedRequest,
} from "./types";

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

/** The feed as stored right now: a form edits what is there, never what was cached. */
export function useFeedForEditing(id: string) {
  return useQuery({ ...feedQuery(id), refetchOnMount: "always" });
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

/** Scrape the front pages now; it answers the feeds this run stored. Never retried. */
export function useScrapeFeeds() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => unwrap(api.GET("/feed/scrap")),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: feedKeys.all }),
  });
}

/** Delete a feed; one that is already gone counts as deleted. Never retried. */
export function useDeleteFeed() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      try {
        await unwrapEmpty(api.DELETE("/feed/{id}", { params: { path: { id } } }));
      } catch (error) {
        if (!(error instanceof ApiError && error.status === 404)) {
          throw error;
        }
      }
    },
    onSuccess: (_, id) => {
      // Gone from the lists at once, without waiting for them to load again.
      queryClient.setQueriesData<InfiniteData<FeedPageResponse>>(
        { queryKey: [...feedKeys.all, "list"] },
        (data) =>
          data && {
            ...data,
            pages: data.pages.map((page) => ({
              ...page,
              items: page.items.filter((feed) => feed.id !== id),
            })),
          },
      );
      queryClient.removeQueries({ queryKey: feedKeys.detail(id) });
      void queryClient.invalidateQueries({ queryKey: feedKeys.all });
    },
  });
}

/** Create a newsroom feed with the id the app generated. Never retried. */
export function useCreateFeed() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, feed }: { id: string; feed: CreateFeedRequest }) =>
      unwrap(api.PUT("/feed/{id}", { params: { path: { id } }, body: feed })),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: feedKeys.all }),
  });
}

/** Change the fields in `changes` of a feed; absent keys keep their value. Never retried. */
export function useUpdateFeed() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, changes }: { id: string; changes: UpdateFeedRequest }) =>
      unwrap(api.PATCH("/feed/{id}", { params: { path: { id } }, body: changes })),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: feedKeys.all }),
  });
}

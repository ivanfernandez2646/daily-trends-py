import { queryOptions, useQuery } from "@tanstack/react-query";
import { api, unwrap } from "./client";

export const feedKeys = {
  all: ["feeds"] as const,
  home: () => [...feedKeys.all, "home"] as const,
};

export const homeFeedsQuery = queryOptions({
  queryKey: feedKeys.home(),
  queryFn: () => unwrap(api.GET("/feed/home")),
});

export function useHomeFeeds() {
  return useQuery(homeFeedsQuery);
}

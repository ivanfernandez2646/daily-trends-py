import type { FeedResponse } from "../../api/types";

const SIDE_COUNT = 3;

/** The lead story, the side column and the rest, in the order the API gives. */
export function splitFrontPage<T>(feeds: readonly T[]): { lead?: T; side: T[]; more: T[] } {
  const [lead, ...rest] = feeds;
  return { lead, side: rest.slice(0, SIDE_COUNT), more: rest.slice(SIDE_COUNT) };
}

export function lastUpdated(feeds: readonly FeedResponse[]): string | undefined {
  return feeds.reduce<string | undefined>(
    (newest, feed) =>
      newest === undefined || Date.parse(feed.created_at) > Date.parse(newest)
        ? feed.created_at
        : newest,
    undefined,
  );
}

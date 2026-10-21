import { delay } from "msw";
import { HttpResponse, http } from "msw/http";
import type { FeedResponse } from "../api/types";
import { server } from "./server";

type FeedListOptions = {
  /** Milliseconds before answering a request, to reorder concurrent answers. */
  delayFor?: (query: Record<string, string>) => number;
};

/**
 * `GET /feed/list` over `feeds`, given newest first: it filters by category, source and any word
 * of `q`, and pages with an opaque cursor, like the API.
 */
export function fakeFeedList(feeds: FeedResponse[], { delayFor = () => 0 }: FeedListOptions = {}) {
  const requests: Record<string, string>[] = [];
  server.use(
    http.get("/feed/list", async ({ request }) => {
      const query = Object.fromEntries(new URL(request.url).searchParams);
      requests.push(query);
      await delay(delayFor(query));
      const words = (query.q ?? "").toLowerCase().split(/\s+/).filter(Boolean);
      const matching = feeds.filter(
        (feed) =>
          (query.category === undefined || feed.category === query.category) &&
          (query.source === undefined || feed.source === query.source) &&
          (words.length === 0 ||
            words.some((word) =>
              `${feed.title} ${feed.description ?? ""}`.toLowerCase().split(/\W+/u).includes(word),
            )),
      );
      const start = query.cursor === undefined ? 0 : Number(atob(query.cursor));
      const end = start + Number(query.limit ?? 20);
      return HttpResponse.json({
        items: matching.slice(start, end),
        next_cursor: end < matching.length ? btoa(String(end)) : null,
      });
    }),
  );
  return { requests: () => requests };
}

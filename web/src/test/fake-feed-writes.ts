import { HttpResponse, http } from "msw/http";
import type { FeedResponse } from "../api/types";
import { server } from "./server";

type WriteRequest = { id: string; authorization: string | null };

/**
 * `DELETE /feed/{id}` over `feeds`, the same array a fake list reads, so a deleted feed leaves the
 * list. An unknown id answers 404, like the API.
 */
export function fakeDeleteFeed(feeds: FeedResponse[]) {
  const requests: WriteRequest[] = [];
  server.use(
    http.delete("/feed/:id", ({ params, request }) => {
      const id = String(params.id);
      requests.push({ id, authorization: request.headers.get("Authorization") });
      const index = feeds.findIndex((feed) => feed.id === id);
      if (index === -1) {
        return HttpResponse.json({ error: `Feed with id <${id}> not found` }, { status: 404 });
      }
      feeds.splice(index, 1);
      return new HttpResponse(null, { status: 204 });
    }),
  );
  return { requests };
}

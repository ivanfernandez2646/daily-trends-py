import { HttpResponse, http } from "msw/http";
import type { CreateFeedRequest, FeedResponse, UpdateFeedRequest } from "../api/types";
import { aFeed } from "./feed-mother";
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

type CreateRequest = WriteRequest & { body: CreateFeedRequest };

/**
 * `PUT /feed/{id}`, which creates a newsroom feed like the API: 201 with the feed, or 409 for an id
 * already used. `taken` makes the first requests find their id taken, as a collision would.
 */
export function fakeCreateFeed({ taken = 0 }: { taken?: number } = {}) {
  const requests: CreateRequest[] = [];
  const ids = new Set<string>();
  server.use(
    http.put("/feed/:id", async ({ params, request }) => {
      const id = String(params.id);
      const body = (await request.json()) as CreateFeedRequest;
      requests.push({ id, body, authorization: request.headers.get("Authorization") });
      if (ids.has(id) || requests.length <= taken) {
        return HttpResponse.json({ error: `Feed with id <${id}> already exists` }, { status: 409 });
      }
      ids.add(id);
      return HttpResponse.json(
        aFeed({ ...body, id, source: "CMS", url: null, description: body.description ?? null }),
        { status: 201 },
      );
    }),
  );
  return { requests };
}

type UpdateRequest = WriteRequest & { body: UpdateFeedRequest };

/**
 * `GET /feed/{id}` and `PATCH /feed/{id}` over `feeds`, the array the other fakes share: an
 * absent key keeps its value and a missing feed answers 404, like the API.
 */
export function fakeFeedDetail(feeds: FeedResponse[]) {
  const reads: string[] = [];
  const updates: UpdateRequest[] = [];
  const notFound = (id: string) =>
    HttpResponse.json({ error: `Feed with id <${id}> not found` }, { status: 404 });
  server.use(
    http.get("/feed/:id", ({ params }) => {
      const id = String(params.id);
      // The list and the front page have their own fakes.
      if (id === "list" || id === "home") {
        return undefined;
      }
      reads.push(id);
      const feed = feeds.find((candidate) => candidate.id === id);
      return feed === undefined ? notFound(id) : HttpResponse.json(feed);
    }),
    http.patch("/feed/:id", async ({ params, request }) => {
      const id = String(params.id);
      const body = (await request.json()) as UpdateFeedRequest;
      updates.push({ id, body, authorization: request.headers.get("Authorization") });
      const index = feeds.findIndex((candidate) => candidate.id === id);
      const feed = feeds[index];
      if (feed === undefined) {
        return notFound(id);
      }
      const updated = { ...feed, ...body, updated_at: new Date().toISOString() };
      feeds[index] = updated;
      return HttpResponse.json(updated);
    }),
  );
  return { reads, updates };
}

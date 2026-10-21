import { HttpResponse, http } from "msw/http";
import { describe, expect, it } from "vitest";
import { aFeed } from "../test/feed-mother";
import { server } from "../test/server";
import { ApiError, api, unwrap } from "./client";

describe("unwrap", () => {
  it("answers the body of a successful response", async () => {
    const feeds = [aFeed(), aFeed()];
    server.use(http.get("/feed/home", () => HttpResponse.json(feeds)));

    await expect(unwrap(api.GET("/feed/home"))).resolves.toEqual(feeds);
  });

  it("throws an ApiError with the status and the API message", async () => {
    server.use(
      http.get("/feed/:id", () => HttpResponse.json({ error: "Feed not found" }, { status: 404 })),
    );

    const request = unwrap(
      api.GET("/feed/{id}", { params: { path: { id: crypto.randomUUID() } } }),
    );

    await expect(request).rejects.toThrow(new ApiError(404, "Feed not found"));
    await expect(request).rejects.toMatchObject({ status: 404 });
  });

  it("lets a network error through, as something other than an ApiError", async () => {
    server.use(http.get("/feed/home", () => HttpResponse.error()));

    const error: unknown = await unwrap(api.GET("/feed/home")).catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(Error);
    expect(error).not.toBeInstanceOf(ApiError);
  });
});

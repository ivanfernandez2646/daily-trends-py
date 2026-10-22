import { HttpResponse, http } from "msw/http";
import { describe, expect, it, onTestFinished } from "vitest";
import { aFeed } from "../test/feed-mother";
import { server } from "../test/server";
import { ApiError, api, sendAccessToken, unwrap, unwrapEmpty } from "./client";

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

describe("unwrapEmpty", () => {
  it("resolves on an answer without a body", async () => {
    server.use(http.delete("/feed/:id", () => new HttpResponse(null, { status: 204 })));

    const request = api.DELETE("/feed/{id}", { params: { path: { id: crypto.randomUUID() } } });

    await expect(unwrapEmpty(request)).resolves.toBeUndefined();
  });

  it("throws an ApiError for an answer outside 2xx", async () => {
    server.use(
      http.delete("/feed/:id", () =>
        HttpResponse.json({ error: "Feed not found" }, { status: 404 }),
      ),
    );

    const request = api.DELETE("/feed/{id}", { params: { path: { id: crypto.randomUUID() } } });

    await expect(unwrapEmpty(request)).rejects.toThrow(new ApiError(404, "Feed not found"));
  });
});

describe("sendAccessToken", () => {
  /** A session that holds `token` and records how it ends. */
  function aHolder(token: string | undefined) {
    const ends: string[] = [];
    const holder = { token: () => token, end: (reason: "expired") => void ends.push(reason) };
    onTestFinished(sendAccessToken(holder));
    return { ends };
  }

  function recordAuthorization() {
    const sent: (string | null)[] = [];
    server.use(
      http.get("/feed/scrap", ({ request }) => {
        sent.push(request.headers.get("Authorization"));
        return HttpResponse.json([]);
      }),
    );
    return sent;
  }

  it("sends the token of an active session as a bearer token", async () => {
    aHolder("a-token");
    const sent = recordAuthorization();

    await unwrap(api.GET("/feed/scrap"));

    expect(sent).toEqual(["Bearer a-token"]);
  });

  it("sends no Authorization header without a session", async () => {
    aHolder(undefined);
    const sent = recordAuthorization();

    await unwrap(api.GET("/feed/scrap"));

    expect(sent).toEqual([null]);
  });

  it("stops sending the token once disconnected", async () => {
    const disconnect = sendAccessToken({ token: () => "a-token", end: () => {} });
    disconnect();
    const sent = recordAuthorization();

    await unwrap(api.GET("/feed/scrap"));

    expect(sent).toEqual([null]);
  });

  it("ends the session when the API rejects its token", async () => {
    const { ends } = aHolder("a-token");
    server.use(
      http.get("/feed/scrap", () =>
        HttpResponse.json({ error: "Invalid or expired access token" }, { status: 401 }),
      ),
    );

    await expect(unwrap(api.GET("/feed/scrap"))).rejects.toMatchObject({ status: 401 });

    expect(ends).toEqual(["expired"]);
  });

  it("keeps the session when the API rejects another token", async () => {
    const { ends } = aHolder("a-token");
    server.use(
      http.get("/auth/me", () =>
        HttpResponse.json({ error: "Invalid or expired access token" }, { status: 401 }),
      ),
    );

    await expect(
      unwrap(api.GET("/auth/me", { headers: { Authorization: "Bearer another-token" } })),
    ).rejects.toMatchObject({ status: 401 });

    expect(ends).toEqual([]);
  });

  it("keeps the session when a public route answers 401", async () => {
    const { ends } = aHolder(undefined);
    server.use(
      http.post("/auth/login", () =>
        HttpResponse.json({ error: "Invalid email or password" }, { status: 401 }),
      ),
    );

    await expect(
      unwrap(api.POST("/auth/login", { body: { email: "a@b.co", password: "wrong" } })),
    ).rejects.toMatchObject({ status: 401 });

    expect(ends).toEqual([]);
  });
});

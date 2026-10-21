import { screen, within } from "@testing-library/react";
import { HttpResponse, http } from "msw/http";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { FeedResponse } from "../api/types";
import { fakeFeedList } from "../test/fake-feed-list";
import { aFeed } from "../test/feed-mother";
import { renderRoute } from "../test/render";
import { server } from "../test/server";

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-21T12:00:00Z"));
});

afterEach(() => {
  vi.useRealTimers();
});

const feed = aFeed({
  title: "El alquiler sube por tercer trimestre consecutivo",
  description: "Madrid y Barcelona concentran las mayores subidas.",
  author: "Laura Martín",
  source: "EL_ESPANOL",
  category: "ECONOMY",
  url: "https://www.elespanol.com/invertia/vivienda/alquiler.html",
  created_at: "2026-10-21T10:40:00Z",
  updated_at: null,
});

/** `GET /feed/{id}` answering `feed`, and nothing else, counting the requests. */
function answerFeed(answer: FeedResponse | { status: number; error: string }) {
  let requests = 0;
  server.use(
    http.get("/feed/:id", ({ params }) => {
      if (params.id === "list" || params.id === "home") {
        return undefined;
      }
      requests += 1;
      return "status" in answer
        ? HttpResponse.json({ error: answer.error }, { status: answer.status })
        : HttpResponse.json(answer);
    }),
  );
  return { requests: () => requests };
}

describe("a feed", () => {
  it("shows its headline, lead-in, category, newspaper, author and dates", async () => {
    answerFeed(feed);
    fakeFeedList([]);

    renderRoute(`/feeds/${feed.id}`);

    expect(await screen.findByRole("heading", { level: 1, name: feed.title })).toBeInTheDocument();
    expect(
      screen.getByText("Madrid y Barcelona concentran las mayores subidas."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Economía" })).toHaveAttribute(
      "href",
      "/feeds?category=ECONOMY",
    );
    expect(screen.getAllByText("El Español").length).toBeGreaterThan(0);
    expect(screen.getByText("Laura Martín")).toBeInTheDocument();
    expect(screen.getByText("21 de octubre de 2026 a las 12:40")).toHaveAttribute(
      "datetime",
      feed.created_at,
    );
    expect(screen.queryByText("Editada")).not.toBeInTheDocument();
  });

  it("says when it was edited", async () => {
    answerFeed({ ...feed, updated_at: "2026-10-21T11:05:00Z" });
    fakeFeedList([]);

    renderRoute(`/feeds/${feed.id}`);

    expect(await screen.findByText("Editada")).toBeInTheDocument();
    expect(screen.getByText("21 de octubre de 2026 a las 13:05")).toHaveAttribute(
      "datetime",
      "2026-10-21T11:05:00Z",
    );
  });

  it("credits its source with the article's address and a link to it", async () => {
    answerFeed(feed);
    fakeFeedList([]);

    renderRoute(`/feeds/${feed.id}`);

    const panel = await screen.findByRole("region", { name: "Fuente original" });
    expect(
      within(panel).getByText("elespanol.com/invertia/vivienda/alquiler.html"),
    ).toBeInTheDocument();
    const link = within(panel).getByRole("link", { name: /^Leer en El Español/ });
    expect(link).toHaveAttribute("href", feed.url);
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("has no source panel without an article", async () => {
    answerFeed({ ...feed, source: "CMS", url: null });
    fakeFeedList([]);

    renderRoute(`/feeds/${feed.id}`);

    await screen.findByRole("heading", { level: 1, name: feed.title });
    expect(screen.queryByRole("region", { name: "Fuente original" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /^Leer en/ })).not.toBeInTheDocument();
  });

  it("shows skeletons while it loads", async () => {
    answerFeed(feed);
    fakeFeedList([]);

    renderRoute(`/feeds/${feed.id}`);

    expect(await screen.findByRole("status")).toHaveTextContent("Cargando la noticia");
    await screen.findByRole("heading", { level: 1, name: feed.title });
  });

  it("offers to try again when the API fails", async () => {
    answerFeed({ status: 500, error: "Internal server error" });

    renderRoute(`/feeds/${feed.id}`);

    expect(await screen.findByRole("alert")).toHaveTextContent("No se han podido cargar");
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
  });
});

describe("more of its category", () => {
  it("shows up to three other feeds of the category, leaving this one out", async () => {
    answerFeed(feed);
    const others = [1, 2, 3].map((index) =>
      aFeed({ title: `Más economía ${index}`, category: "ECONOMY" }),
    );
    const api = fakeFeedList(
      [others[0], feed, others[1], others[2]].filter((item) => item !== undefined),
    );

    renderRoute(`/feeds/${feed.id}`);

    const related = await screen.findByRole("region", { name: "Más de Economía" });
    expect(
      within(related)
        .getAllByRole("link")
        .map((link) => link.textContent),
    ).toEqual(["Más economía 1", "Más economía 2", "Más economía 3"]);
    expect(api.requests()).toEqual([{ category: "ECONOMY", limit: "4" }]);
  });

  it("keeps three when this feed is not among them", async () => {
    answerFeed(feed);
    fakeFeedList(
      [1, 2, 3, 4].map((index) => aFeed({ title: `Más economía ${index}`, category: "ECONOMY" })),
    );

    renderRoute(`/feeds/${feed.id}`);

    const related = await screen.findByRole("region", { name: "Más de Economía" });
    expect(within(related).getAllByRole("listitem")).toHaveLength(3);
  });

  it("is hidden when there are none", async () => {
    answerFeed(feed);
    const api = fakeFeedList([feed]);

    renderRoute(`/feeds/${feed.id}`);

    await screen.findByRole("heading", { level: 1, name: feed.title });
    await vi.waitFor(() => expect(api.requests()).toHaveLength(1));
    expect(screen.queryByRole("region", { name: /^Más de/ })).not.toBeInTheDocument();
  });
});

describe("a feed that does not exist", () => {
  it.each([
    [404, "Feed not found"],
    [400, "<FeedId> does not allow the value <nope>"],
  ])("shows the not found page for a %i, without retrying", async (status, error) => {
    const api = answerFeed({ status, error });

    renderRoute("/feeds/nope");

    expect(
      await screen.findByRole("heading", { level: 1, name: "No encontramos esta noticia." }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Volver a la portada" })).toHaveAttribute("href", "/");
    expect(api.requests()).toBe(1);
  });
});

it("has its landmarks and a single h1", async () => {
  answerFeed(feed);
  fakeFeedList([]);

  renderRoute(`/feeds/${feed.id}`);

  await screen.findByRole("heading", { level: 1, name: feed.title });
  expect(screen.getByRole("banner")).toBeInTheDocument();
  expect(screen.getByRole("main")).toBeInTheDocument();
  expect(screen.getByRole("contentinfo")).toBeInTheDocument();
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
});

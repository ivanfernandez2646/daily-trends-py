import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw/http";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { FeedResponse } from "../api/types";
import { aFeed } from "../test/feed-mother";
import { renderRoute } from "../test/render";
import { server } from "../test/server";

const NOW = new Date("2026-10-21T10:00:00Z");

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(NOW);
});

afterEach(() => {
  vi.useRealTimers();
});

/** Feeds newest first, one minute apart from 09:46 UTC, as the API answers them. */
function frontPage(count: number): FeedResponse[] {
  return Array.from({ length: count }, (_, index) =>
    aFeed({
      title: `Titular ${index + 1}`,
      created_at: new Date(Date.parse("2026-10-21T09:46:00Z") - index * 60_000).toISOString(),
    }),
  );
}

function answerHome(feeds: FeedResponse[]): void {
  server.use(http.get("/feed/home", () => HttpResponse.json(feeds)));
}

function headlines(level: number): string[] {
  return screen.getAllByRole("heading", { level }).map((heading) => heading.textContent ?? "");
}

it("shows skeletons while the front page loads", async () => {
  let answer: (feeds: FeedResponse[]) => void = () => {};
  server.use(
    http.get("/feed/home", async () => {
      const feeds = await new Promise<FeedResponse[]>((resolve) => {
        answer = resolve;
      });
      return HttpResponse.json(feeds);
    }),
  );

  renderRoute("/");

  expect(await screen.findByRole("status")).toHaveTextContent("Cargando noticias");
  answer(frontPage(1));
  expect(await screen.findByRole("heading", { name: "Titular 1" })).toBeInTheDocument();
  expect(screen.queryByText("Cargando noticias")).not.toBeInTheDocument();
});

describe("with 10 feeds", () => {
  it("shows the lead, a side column of three and six more headlines", async () => {
    answerHome(frontPage(10));

    renderRoute("/");

    const lead = await screen.findByRole("region", { name: "Destacadas" });
    expect(within(lead).getAllByRole("heading", { level: 2 })[0]).toHaveTextContent("Titular 1");
    expect(
      within(lead)
        .getAllByRole("heading", { level: 3 })
        .map((h) => h.textContent),
    ).toEqual(["Titular 2", "Titular 3", "Titular 4"]);
    const more = screen.getByRole("region", { name: "Más titulares" });
    expect(
      within(more)
        .getAllByRole("heading", { level: 3 })
        .map((h) => h.textContent),
    ).toEqual(["Titular 5", "Titular 6", "Titular 7", "Titular 8", "Titular 9", "Titular 10"]);
    expect(within(more).getByRole("link", { name: "Ver todas las noticias →" })).toHaveAttribute(
      "href",
      "/feeds",
    );
  });

  it("links each headline to its feed's page", async () => {
    const feeds = frontPage(10);
    answerHome(feeds);

    renderRoute("/");

    for (const feed of feeds) {
      expect(await screen.findByRole("link", { name: feed.title })).toHaveAttribute(
        "href",
        `/feeds/${feed.id}`,
      );
    }
  });

  it("says when the front page was last updated", async () => {
    answerHome(frontPage(10));

    renderRoute("/");

    expect(await screen.findByText("Actualizado hace 14 min")).toBeInTheDocument();
  });
});

it("shows a lead and a side column of three for 4 feeds, without more headlines", async () => {
  answerHome(frontPage(4));

  renderRoute("/");

  await screen.findByRole("heading", { name: "Titular 1" });
  expect(headlines(3)).toEqual(["Titular 2", "Titular 3", "Titular 4"]);
  expect(screen.queryByRole("region", { name: "Más titulares" })).not.toBeInTheDocument();
});

it("shows a single feed as the lead alone", async () => {
  answerHome(frontPage(1));

  renderRoute("/");

  await screen.findByRole("heading", { name: "Titular 1" });
  expect(screen.queryAllByRole("heading", { level: 3 })).toEqual([]);
  expect(screen.queryByRole("region", { name: "Más titulares" })).not.toBeInTheDocument();
});

it("explains an empty front page", async () => {
  answerHome([]);

  renderRoute("/");

  expect(
    await screen.findByText(
      "Aún no hay noticias. La portada se llenará cuando se lean los periódicos.",
    ),
  ).toBeInTheDocument();
  expect(screen.queryByText(/^Actualizado/)).not.toBeInTheDocument();
});

it("links the lead to its article in a new tab", async () => {
  const [lead, ...rest] = frontPage(4);
  if (lead === undefined) throw new Error("no lead");
  answerHome([{ ...lead, source: "EL_MUNDO", url: "https://www.elmundo.es/a.html" }, ...rest]);

  renderRoute("/");

  const link = await screen.findByRole("link", { name: /^Leer en El Mundo/ });
  expect(link).toHaveAttribute("href", "https://www.elmundo.es/a.html");
  expect(link).toHaveAttribute("target", "_blank");
  expect(link).toHaveAttribute("rel", "noopener noreferrer");
});

it("has no source link for a newsroom feed", async () => {
  answerHome([aFeed({ title: "Nota de la redacción", source: "CMS", url: null })]);

  renderRoute("/");

  await screen.findByRole("heading", { name: "Nota de la redacción" });
  expect(screen.queryByRole("link", { name: /^Leer en/ })).not.toBeInTheDocument();
});

describe("when the API fails", () => {
  it("offers to try again instead of an empty front page", async () => {
    let fails = true;
    server.use(
      http.get("/feed/home", () =>
        fails
          ? HttpResponse.json({ error: "Internal server error" }, { status: 500 })
          : HttpResponse.json(frontPage(1)),
      ),
    );

    renderRoute("/");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "No se han podido cargar las noticias. Comprueba tu conexión e inténtalo de nuevo.",
    );
    expect(screen.queryByText(/^Aún no hay noticias/)).not.toBeInTheDocument();

    fails = false;
    await userEvent.click(within(alert).getByRole("button", { name: "Reintentar" }));

    expect(await screen.findByRole("heading", { name: "Titular 1" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("keeps the API's message out of the page", async () => {
    server.use(
      http.get("/feed/home", () =>
        HttpResponse.json({ error: "Internal server error" }, { status: 500 }),
      ),
    );
    const logged: string[] = [];

    renderRoute("/", { log: (message) => logged.push(message) });

    await screen.findByRole("alert");
    expect(screen.queryByText(/Internal server error/)).not.toBeInTheDocument();
    await waitFor(() => expect(logged).toEqual(["API 500: Internal server error"]));
  });

  it("shows the same notice when the network fails", async () => {
    server.use(http.get("/feed/home", () => HttpResponse.error()));

    renderRoute("/");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No se han podido cargar las noticias.",
    );
  });
});

it("has its landmarks and a single h1", async () => {
  answerHome(frontPage(10));

  renderRoute("/");

  await screen.findByRole("heading", { name: "Titular 1" });
  expect(screen.getByRole("banner")).toBeInTheDocument();
  expect(screen.getByRole("main")).toBeInTheDocument();
  expect(screen.getByRole("contentinfo")).toHaveTextContent(
    "Cada noticia enlaza a su fuente original",
  );
  expect(headlines(1)).toEqual(["Daily Trends"]);
});

import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw/http";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { FeedResponse } from "../api/types";
import { CATEGORIES, categoryLabel } from "../lib/labels";
import { fakeFeedList } from "../test/fake-feed-list";
import { aFeed } from "../test/feed-mother";
import { renderRoute } from "../test/render";
import { server } from "../test/server";

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-21T10:00:00Z"));
});

afterEach(() => {
  vi.useRealTimers();
});

/** Feeds newest first, an hour apart from 09:00 UTC today (11:00 in Madrid). */
function feedsNewestFirst(count: number, overrides: Partial<FeedResponse> = {}): FeedResponse[] {
  return Array.from({ length: count }, (_, index) =>
    aFeed({
      title: `Noticia ${index + 1}`,
      created_at: new Date(Date.parse("2026-10-21T09:00:00Z") - index * 3_600_000).toISOString(),
      ...overrides,
    }),
  );
}

function rowHeadlines(): string[] {
  return screen.getAllByRole("heading", { level: 2 }).map((heading) => heading.textContent ?? "");
}

async function waitForRows(count: number): Promise<void> {
  await waitFor(() => expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(count));
}

describe("the list", () => {
  it("shows the first 20 feeds newest first, with their time and day", async () => {
    fakeFeedList(feedsNewestFirst(25));

    renderRoute("/feeds");

    await waitForRows(20);
    expect(rowHeadlines().slice(0, 2)).toEqual(["Noticia 1", "Noticia 2"]);
    const first = within(screen.getByRole("list", { name: "Noticias" })).getAllByRole(
      "listitem",
    )[0];
    expect(first).toBeDefined();
    expect(within(first as HTMLElement).getByText("11:00")).toBeInTheDocument();
    expect(within(first as HTMLElement).getByText("Hoy")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Explorar" })).toBeInTheDocument();
  });

  it("loads the next page until there is none", async () => {
    const api = fakeFeedList(feedsNewestFirst(25));
    renderRoute("/feeds");
    await waitForRows(20);

    await userEvent.click(screen.getByRole("button", { name: "Cargar más" }));

    await waitForRows(25);
    expect(rowHeadlines().at(-1)).toBe("Noticia 25");
    expect(api.requests().at(-1)).toEqual({ limit: "20", cursor: btoa("20") });
    expect(screen.queryByRole("button", { name: "Cargar más" })).not.toBeInTheDocument();
  });

  it("shows skeletons while it loads", async () => {
    fakeFeedList(feedsNewestFirst(1), { delayFor: () => 50 });

    renderRoute("/feeds");

    expect(await screen.findByRole("status")).toHaveTextContent("Cargando noticias");
    await waitForRows(1);
  });

  it("offers to try again when the API fails", async () => {
    server.use(
      http.get("/feed/list", () =>
        HttpResponse.json({ error: "Internal server error" }, { status: 500 }),
      ),
    );

    renderRoute("/feeds");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No se han podido cargar las noticias.",
    );
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
  });
});

describe("the category", () => {
  const mixed = [
    ...feedsNewestFirst(3, { category: "SPORTS" }),
    ...feedsNewestFirst(2, { category: "CULTURE" }),
  ];

  it("filters by the pressed chip and keeps it in the URL", async () => {
    const api = fakeFeedList(mixed);
    const { router } = renderRoute("/feeds");
    await waitForRows(5);

    await userEvent.click(screen.getByRole("button", { name: "Deportes" }));

    await waitForRows(3);
    expect(router.state.location.search).toEqual({ category: "SPORTS" });
    expect(api.requests().at(-1)).toEqual({ limit: "20", category: "SPORTS" });
    expect(screen.getByRole("button", { name: "Deportes" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("shows every category again with Todas", async () => {
    fakeFeedList(mixed);
    const { router } = renderRoute("/feeds?category=SPORTS");
    await waitForRows(3);

    await userEvent.click(screen.getByRole("button", { name: "Todas" }));

    await waitForRows(5);
    expect(router.state.location.search).toEqual({});
    expect(screen.getByRole("button", { name: "Todas" })).toHaveAttribute("aria-pressed", "true");
  });

  it("restores the previous filters when going back", async () => {
    fakeFeedList(mixed);
    const { router } = renderRoute("/feeds");
    await waitForRows(5);
    await userEvent.click(screen.getByRole("button", { name: "Deportes" }));
    await waitForRows(3);

    act(() => router.history.back());

    await waitForRows(5);
    expect(screen.getByRole("button", { name: "Todas" })).toHaveAttribute("aria-pressed", "true");
  });

  it("never lets an older answer replace a newer one", async () => {
    fakeFeedList(mixed, { delayFor: (query) => (query.category === "SPORTS" ? 150 : 0) });
    renderRoute("/feeds");
    await waitForRows(5);

    await userEvent.click(screen.getByRole("button", { name: "Deportes" }));
    await userEvent.click(screen.getByRole("button", { name: "Cultura" }));

    await waitForRows(2);
    await act(() => new Promise((resolve) => setTimeout(resolve, 250)));
    expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(2);
  });

  it("starts again from the first page", async () => {
    const api = fakeFeedList([
      ...feedsNewestFirst(25, { category: "SPORTS" }),
      ...feedsNewestFirst(1, { category: "CULTURE" }),
    ]);
    renderRoute("/feeds");
    await waitForRows(20);
    await userEvent.click(screen.getByRole("button", { name: "Cargar más" }));
    await waitForRows(26);

    await userEvent.click(screen.getByRole("button", { name: "Deportes" }));

    await waitForRows(20);
    expect(api.requests().at(-1)).toEqual({ limit: "20", category: "SPORTS" });
  });
});

describe("the newspaper", () => {
  it("filters by the selected newspaper", async () => {
    const api = fakeFeedList([
      ...feedsNewestFirst(2, { source: "EL_MUNDO" }),
      ...feedsNewestFirst(1, { source: "LA_RAZON" }),
    ]);
    const { router } = renderRoute("/feeds");
    await waitForRows(3);

    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Periódico" }), "La Razón");

    await waitForRows(1);
    expect(router.state.location.search).toEqual({ source: "LA_RAZON" });
    expect(api.requests().at(-1)).toEqual({ limit: "20", source: "LA_RAZON" });
  });

  it("offers every scraped newspaper and the newsroom", async () => {
    fakeFeedList([]);

    renderRoute("/feeds");

    const select = await screen.findByRole("combobox", { name: "Periódico" });
    expect(
      within(select)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual([
      "Todos",
      "El Mundo",
      "El Español",
      "El Confidencial",
      "La Razón",
      "La Vanguardia",
      "Redacción",
    ]);
  });
});

describe("the search", () => {
  const feeds = [aFeed({ title: "Lluvias en madrid" }), aFeed({ title: "Mercados en calma" })];

  it("asks once for what was typed quickly", async () => {
    const api = fakeFeedList(feeds);
    const { router } = renderRoute("/feeds");
    await waitForRows(2);

    await userEvent.type(screen.getByRole("searchbox", { name: "Buscar noticias" }), "madrid");

    await waitForRows(1);
    await act(() => new Promise((resolve) => setTimeout(resolve, 350)));
    expect(api.requests().filter((query) => query.q !== undefined)).toEqual([
      { limit: "20", q: "madrid" },
    ]);
    expect(router.state.location.search).toEqual({ q: "madrid" });
  });

  it("applies at once on Enter", async () => {
    fakeFeedList(feeds);
    const { router } = renderRoute("/feeds");
    await waitForRows(2);

    await userEvent.type(
      screen.getByRole("searchbox", { name: "Buscar noticias" }),
      "madrid{Enter}",
    );

    expect(router.state.location.search).toEqual({ q: "madrid" });
  });

  it("removes the search when the box is cleared", async () => {
    const api = fakeFeedList(feeds);
    const { router } = renderRoute("/feeds?q=madrid");
    await waitForRows(1);

    await userEvent.clear(screen.getByRole("searchbox", { name: "Buscar noticias" }));

    await waitForRows(2);
    expect(router.state.location.search).toEqual({});
    expect(api.requests().at(-1)).toEqual({ limit: "20" });
  });

  it("is focused when the reader came to search", async () => {
    fakeFeedList(feeds);

    renderRoute("/feeds#buscar");

    await waitFor(() =>
      expect(screen.getByRole("searchbox", { name: "Buscar noticias" })).toHaveFocus(),
    );
  });
});

describe("the filters in the URL", () => {
  it("pre-selects them and names them in the summary", async () => {
    const api = fakeFeedList([
      aFeed({ title: "Derbi en madrid", category: "SPORTS", source: "EL_MUNDO" }),
    ]);

    renderRoute("/feeds?category=SPORTS&source=EL_MUNDO&q=madrid");

    await waitForRows(1);
    expect(api.requests()).toEqual([
      { limit: "20", category: "SPORTS", source: "EL_MUNDO", q: "madrid" },
    ]);
    expect(screen.getByRole("button", { name: "Deportes" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("combobox", { name: "Periódico" })).toHaveValue("EL_MUNDO");
    expect(screen.getByRole("searchbox", { name: "Buscar noticias" })).toHaveValue("madrid");
    expect(screen.getByText("Noticias con “madrid” en Deportes de El Mundo")).toBeInTheDocument();
  });

  it("clears them all at once", async () => {
    fakeFeedList(feedsNewestFirst(2, { category: "SPORTS" }));
    const { router } = renderRoute("/feeds?category=SPORTS&q=noticia");
    await waitForRows(2);

    await userEvent.click(screen.getByRole("button", { name: "Limpiar filtros" }));

    await waitFor(() => expect(router.state.location.search).toEqual({}));
    expect(screen.getByRole("searchbox", { name: "Buscar noticias" })).toHaveValue("");
    expect(screen.queryByRole("button", { name: "Limpiar filtros" })).not.toBeInTheDocument();
  });

  it.each([
    ["/feeds?category=nope", {}],
    ["/feeds?category=SPORTS&source=ABC", { category: "SPORTS" }],
    ["/feeds?q=%20%20", {}],
  ])("drops invalid values from %s before asking the API", async (path, kept) => {
    const api = fakeFeedList(feedsNewestFirst(1, { category: "SPORTS" }));

    const { router } = renderRoute(path);

    await waitForRows(1);
    expect(router.state.location.search).toEqual(kept);
    expect(router.state.location.href).not.toMatch(/nope|ABC|%20/);
    expect(api.requests()).toEqual([{ limit: "20", ...kept }]);
  });

  it("names the filters when nothing matches and offers to clear them", async () => {
    fakeFeedList([]);

    renderRoute("/feeds?category=CULTURE&q=ópera");

    expect(await screen.findByText("No hay noticias con “ópera” en Cultura.")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Limpiar filtros" }).length).toBeGreaterThan(0);
  });
});

it("counts the active filters on the button that opens them on a phone", async () => {
  fakeFeedList([]);
  renderRoute("/feeds?category=SPORTS&source=EL_MUNDO");

  const button = await screen.findByRole("button", { name: /^Filtros/ });
  expect(button).toHaveAccessibleName("Filtros (2 activos)");
  expect(button).toHaveAttribute("aria-expanded", "false");

  await userEvent.click(button);

  expect(button).toHaveAttribute("aria-expanded", "true");
});

it("offers Todas and every category", async () => {
  fakeFeedList([]);

  renderRoute("/feeds");

  const chips = await screen.findByRole("group", { name: "Categoría" });
  expect(
    within(chips)
      .getAllByRole("button")
      .map((chip) => chip.textContent),
  ).toEqual(["Todas", ...CATEGORIES.map(categoryLabel)]);
});

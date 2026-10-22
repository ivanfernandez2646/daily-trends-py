import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw/http";
import { describe, expect, it } from "vitest";
import type { FeedResponse } from "../api/types";
import { fakeAuth } from "../test/fake-auth";
import { fakeFeedList } from "../test/fake-feed-list";
import { fakeDeleteFeed } from "../test/fake-feed-writes";
import { aFeed } from "../test/feed-mother";
import { renderRoute } from "../test/render";
import { server } from "../test/server";

/** Feeds newest first, an hour apart. */
function feedsNewestFirst(count: number, overrides: Partial<FeedResponse> = {}): FeedResponse[] {
  return Array.from({ length: count }, (_, index) =>
    aFeed({
      title: `Noticia ${index + 1}`,
      created_at: new Date(Date.parse("2026-10-21T09:00:00Z") - index * 3_600_000).toISOString(),
      ...overrides,
    }),
  );
}

/** The CMS list of an administrator with a session. */
function renderAdmin(path = "/admin") {
  const token = fakeAuth().signedIn();
  return { token, ...renderRoute(path) };
}

function table() {
  return screen.getByRole("table", { name: "Noticias" });
}

function headlines(): string[] {
  return within(table())
    .getAllByRole("row")
    .slice(1)
    .map((row) => within(row).getAllByRole("cell")[0]?.textContent ?? "");
}

async function waitForRows(count: number) {
  await waitFor(() => expect(headlines()).toHaveLength(count));
}

describe("the table", () => {
  it("shows the first 20 feeds with their newspaper, category, date and actions", async () => {
    const feeds = feedsNewestFirst(25);
    feeds[0] = aFeed({
      ...feeds[0],
      title: "El alquiler sube",
      source: "EL_ESPANOL",
      category: "ECONOMY",
    });
    fakeFeedList(feeds);

    renderAdmin();

    await waitForRows(20);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Noticias");
    const columns = within(table())
      .getAllByRole("columnheader")
      .map((header) => header.textContent);
    expect(columns).toEqual(["Titular", "Periódico", "Categoría", "Fecha", "Acciones"]);
    const first = within(table()).getAllByRole("row")[1] as HTMLElement;
    expect(within(first).getByRole("link", { name: "El alquiler sube" })).toHaveAttribute(
      "href",
      `/feeds/${feeds[0]?.id}`,
    );
    expect(first).toHaveTextContent("El Español");
    expect(first).toHaveTextContent("Economía");
    expect(within(first).getByRole("button", { name: "Borrar «El alquiler sube»" })).toBeEnabled();
    expect(within(first).getByRole("button", { name: "Editar «El alquiler sube»" })).toBeDisabled();
  });

  it("loads the next page until there is none", async () => {
    const list = fakeFeedList(feedsNewestFirst(25));
    renderAdmin();
    await waitForRows(20);

    await userEvent.click(screen.getByRole("button", { name: "Cargar más" }));

    await waitForRows(25);
    expect(screen.queryByRole("button", { name: "Cargar más" })).not.toBeInTheDocument();
    expect(list.requests().at(-1)?.cursor).toBeDefined();
  });

  it("says when there are no feeds", async () => {
    fakeFeedList([]);
    renderAdmin();

    expect(await screen.findByText("Todavía no hay noticias.")).toBeInTheDocument();
  });

  it("offers to try again when the list cannot be loaded", async () => {
    server.use(http.get("/feed/list", () => HttpResponse.json({}, { status: 500 })));
    renderAdmin();

    expect(await screen.findByRole("button", { name: "Reintentar" })).toBeInTheDocument();
  });
});

describe("the filters", () => {
  it("filter by category, newspaper and words, in the URL", async () => {
    const list = fakeFeedList([
      aFeed({ title: "Gol en Madrid", category: "SPORTS", source: "EL_MUNDO" }),
      aFeed({ title: "Gol en Barcelona", category: "SPORTS", source: "LA_VANGUARDIA" }),
      aFeed({ title: "Presupuestos", category: "POLITICS", source: "EL_MUNDO" }),
    ]);
    const { router } = renderAdmin();
    await waitForRows(3);

    await userEvent.click(screen.getByRole("button", { name: "Deportes" }));
    await waitForRows(2);
    await userEvent.selectOptions(screen.getByLabelText("Periódico"), "EL_MUNDO");
    await waitForRows(1);

    expect(headlines()).toEqual(["Gol en Madrid"]);
    expect(router.state.location.search).toEqual({ category: "SPORTS", source: "EL_MUNDO" });
    expect(list.requests().at(-1)).toMatchObject({ category: "SPORTS", source: "EL_MUNDO" });
  });

  it("start from the URL, and the invalid ones are dropped", async () => {
    const list = fakeFeedList([aFeed({ title: "Gol", category: "SPORTS" })]);
    const { router } = renderAdmin("/admin?category=SPORTS&source=nope&q=gol");

    await waitForRows(1);

    expect(router.state.location.search).toEqual({ category: "SPORTS", q: "gol" });
    expect(list.requests()[0]).toMatchObject({ category: "SPORTS", q: "gol" });
    expect(list.requests()[0]).not.toHaveProperty("source");
    expect(screen.getByRole("searchbox", { name: "Buscar noticias" })).toHaveValue("gol");
  });

  it("say when nothing matches, and clear", async () => {
    fakeFeedList([aFeed({ category: "POLITICS" })]);
    const { router } = renderAdmin("/admin?category=SPORTS");

    expect(await screen.findByText("No hay noticias en Deportes.")).toBeInTheDocument();
    await userEvent.click(
      screen.getAllByRole("button", { name: "Limpiar filtros" })[0] as HTMLElement,
    );

    await waitForRows(1);
    expect(router.state.location.search).toEqual({});
  });
});

describe("updating the front pages", () => {
  function fakeScrape(answer: () => Promise<Response> | Response) {
    const authorizations: (string | null)[] = [];
    server.use(
      http.get("/feed/scrap", ({ request }) => {
        authorizations.push(request.headers.get("Authorization"));
        return answer();
      }),
    );
    return { authorizations };
  }

  it("waits for the run, disabled, then counts the new feeds and refreshes the list", async () => {
    const list = fakeFeedList(feedsNewestFirst(2));
    let finish = () => {};
    const finished = new Promise<void>((resolve) => {
      finish = resolve;
    });
    const scrape = fakeScrape(async () => {
      await finished;
      return HttpResponse.json(feedsNewestFirst(3));
    });
    const { token } = renderAdmin();
    await waitForRows(2);
    const listRequests = list.requests().length;

    await userEvent.click(screen.getByRole("button", { name: "Actualizar portadas" }));

    expect(await screen.findByRole("button", { name: "Actualizando…" })).toBeDisabled();
    finish();
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Portadas actualizadas: 3 noticias nuevas",
    );
    expect(screen.getByRole("button", { name: "Actualizar portadas" })).toBeEnabled();
    await waitFor(() => expect(list.requests().length).toBeGreaterThan(listRequests));
    expect(scrape.authorizations).toEqual([`Bearer ${token}`]);
  });

  it.each([
    [1, "Portadas actualizadas: 1 noticia nueva"],
    [0, "No hay noticias nuevas"],
  ])("says so when %i feeds are new", async (count, message) => {
    fakeFeedList([]);
    fakeScrape(() => HttpResponse.json(feedsNewestFirst(count)));
    renderAdmin();

    await userEvent.click(await screen.findByRole("button", { name: "Actualizar portadas" }));

    expect(await screen.findByRole("status")).toHaveTextContent(message);
  });

  it("says it failed, with the API's reason, without trying again", async () => {
    fakeFeedList([]);
    const scrape = fakeScrape(() =>
      HttpResponse.json({ error: "Internal server error" }, { status: 500 }),
    );
    renderAdmin();

    await userEvent.click(await screen.findByRole("button", { name: "Actualizar portadas" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("No se pudieron actualizar las portadas");
    expect(alert).toHaveTextContent("Internal server error");
    expect(scrape.authorizations).toHaveLength(1);
  });

  it("sends the user to log in when the session is no longer valid", async () => {
    fakeFeedList([]);
    fakeScrape(() =>
      HttpResponse.json({ error: "Invalid or expired access token" }, { status: 401 }),
    );
    const { router } = renderAdmin();

    await userEvent.click(await screen.findByRole("button", { name: "Actualizar portadas" }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/login"));
    expect(router.state.location.search).toEqual({ redirect: "/admin" });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

describe("deleting a feed", () => {
  async function askToDelete(title: string) {
    await userEvent.click(await screen.findByRole("button", { name: `Borrar «${title}»` }));
    return screen.getByRole("alertdialog", { name: "¿Borrar esta noticia?" });
  }

  it("asks first, showing the title, and sends nothing when cancelled", async () => {
    const feeds = [aFeed({ title: "El alquiler sube" })];
    fakeFeedList(feeds);
    const deletes = fakeDeleteFeed(feeds);
    renderAdmin();

    const dialog = await askToDelete("El alquiler sube");

    expect(dialog).toHaveTextContent("El alquiler sube");
    expect(dialog).toHaveTextContent("Esta acción no se puede deshacer.");
    await userEvent.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(deletes.requests).toEqual([]);
  });

  it("removes the feed from the list once deleted", async () => {
    const feeds = [aFeed({ title: "El alquiler sube" }), aFeed({ title: "Otra noticia" })];
    const [deleted] = feeds;
    fakeFeedList(feeds);
    const deletes = fakeDeleteFeed(feeds);
    const { token } = renderAdmin();

    const dialog = await askToDelete("El alquiler sube");
    await userEvent.click(within(dialog).getByRole("button", { name: "Borrar" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Noticia borrada");
    await waitFor(() => expect(headlines()).toEqual(["Otra noticia"]));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(deletes.requests).toEqual([{ id: deleted?.id, authorization: `Bearer ${token}` }]);
  });

  it("treats a feed someone else deleted as deleted", async () => {
    const feeds = [aFeed({ title: "El alquiler sube" })];
    fakeFeedList(feeds);
    fakeDeleteFeed([]);
    renderAdmin();
    const dialog = await askToDelete("El alquiler sube");

    // Another administrator deletes it while the dialog is open.
    feeds.splice(0);
    await userEvent.click(within(dialog).getByRole("button", { name: "Borrar" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Noticia borrada");
    await waitFor(() => expect(screen.queryByRole("table")).not.toBeInTheDocument());
  });

  it("keeps the feed and says why when the API fails, without trying again", async () => {
    fakeFeedList([aFeed({ title: "El alquiler sube" })]);
    const requests: string[] = [];
    server.use(
      http.delete("/feed/:id", ({ params }) => {
        requests.push(String(params.id));
        return HttpResponse.json({ error: "Internal server error" }, { status: 500 });
      }),
    );
    renderAdmin();

    const dialog = await askToDelete("El alquiler sube");
    await userEvent.click(within(dialog).getByRole("button", { name: "Borrar" }));

    const alert = await within(dialog).findByRole("alert");
    expect(alert).toHaveTextContent("No se pudo borrar la noticia");
    expect(alert).toHaveTextContent("Internal server error");
    expect(requests).toHaveLength(1);
    // The rest of the page is hidden from assistive technology while the dialog is open.
    await userEvent.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    expect(headlines()).toEqual(["El alquiler sube"]);
  });
});

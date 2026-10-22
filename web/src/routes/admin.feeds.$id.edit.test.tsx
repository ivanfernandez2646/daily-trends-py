import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw/http";
import { describe, expect, it } from "vitest";
import type { FeedResponse } from "../api/types";
import { fakeAuth } from "../test/fake-auth";
import { fakeFeedList } from "../test/fake-feed-list";
import { fakeDeleteFeed, fakeFeedDetail } from "../test/fake-feed-writes";
import { aFeed } from "../test/feed-mother";
import { renderRoute } from "../test/render";
import { server } from "../test/server";

const ADMIN = { email: "admin@example.com", password: "a-long-enough-secret" };

function aScrapedFeed(overrides: Partial<FeedResponse> = {}) {
  return aFeed({
    title: "El alquiler sube por tercer trimestre",
    description: "Madrid y Barcelona concentran las subidas.",
    author: "Laura Martín",
    source: "EL_ESPANOL",
    category: "ECONOMY",
    url: "https://www.elespanol.com/invertia/alquiler.html",
    ...overrides,
  });
}

/** The edit form of `feed` for an administrator with a session, and the list it returns to. */
async function renderEdit(feed: FeedResponse = aScrapedFeed(), session = {}) {
  const auth = fakeAuth();
  const token = auth.signedIn(session);
  const feeds = [feed];
  fakeFeedList(feeds);
  const api = fakeFeedDetail(feeds);
  const deletes = fakeDeleteFeed(feeds);
  const rendered = renderRoute(`/admin/feeds/${feed.id}/edit`);
  await screen.findByRole("heading", { level: 1 });
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Editar noticia");
  // The heading shows at once; the fields once the feed has loaded.
  await screen.findByLabelText("Titular");
  return { auth, token, feed, feeds, api, deletes, ...rendered };
}

function saveButton() {
  return screen.getByRole("button", { name: "Guardar cambios" });
}

async function replace(label: string, text: string) {
  const field = screen.getByLabelText(label);
  await userEvent.clear(field);
  if (text !== "") {
    await userEvent.type(field, text);
  }
}

describe("the form", () => {
  it("is reached from the CMS list", async () => {
    const feed = aScrapedFeed();
    fakeAuth().signedIn();
    fakeFeedList([feed]);
    renderRoute("/admin");

    expect(await screen.findByRole("link", { name: `Editar «${feed.title}»` })).toHaveAttribute(
      "href",
      `/admin/feeds/${feed.id}/edit`,
    );
  });

  it("is filled with the feed, showing what cannot change as text", async () => {
    await renderEdit();

    expect(screen.getByLabelText("Titular")).toHaveValue("El alquiler sube por tercer trimestre");
    expect(screen.getByLabelText("Entradilla (opcional)")).toHaveValue(
      "Madrid y Barcelona concentran las subidas.",
    );
    expect(screen.getByRole("button", { name: "Economía" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.queryByLabelText("Autor")).not.toBeInTheDocument();
    const fixed = screen.getByRole("group", { name: "No se puede cambiar" });
    expect(fixed).toHaveTextContent("Laura Martín");
    expect(fixed).toHaveTextContent("El Español");
    expect(within(fixed).getByRole("link", { name: /elespanol\.com/ })).toHaveAttribute(
      "href",
      "https://www.elespanol.com/invertia/alquiler.html",
    );
    expect(fixed).toHaveTextContent("El autor, el periódico y el enlace no se pueden cambiar");
  });

  it("saves nothing until something changes, and again once the change is undone", async () => {
    await renderEdit();
    expect(saveButton()).toBeDisabled();

    await userEvent.type(screen.getByLabelText("Titular"), "!");
    expect(saveButton()).toBeEnabled();

    await userEvent.type(screen.getByLabelText("Titular"), "{Backspace}");
    expect(saveButton()).toBeDisabled();
  });
});

describe("saving", () => {
  it("sends only the changed fields and returns to the list", async () => {
    const { api, token, router, feed } = await renderEdit();

    await replace("Titular", "El alquiler baja");
    await userEvent.click(screen.getByRole("button", { name: "Sociedad" }));
    await userEvent.click(saveButton());

    await waitFor(() => expect(router.state.location.pathname).toBe("/admin"));
    expect(await screen.findByRole("status")).toHaveTextContent("Cambios guardados");
    expect(api.updates).toEqual([
      {
        id: feed.id,
        body: { title: "El alquiler baja", category: "SOCIETY" },
        authorization: `Bearer ${token}`,
      },
    ]);
  });

  it("clears an emptied description with null", async () => {
    const { api, router } = await renderEdit();

    await replace("Entradilla (opcional)", "");
    await userEvent.click(saveButton());

    await waitFor(() => expect(router.state.location.pathname).toBe("/admin"));
    expect(api.updates.map((update) => update.body)).toEqual([{ description: null }]);
  });

  it("asks for a title before sending anything", async () => {
    const { api } = await renderEdit();

    await replace("Titular", "  ");
    await userEvent.click(saveButton());

    expect(screen.getByLabelText("Titular")).toHaveAccessibleDescription("Escribe un titular");
    expect(api.updates).toEqual([]);
  });

  it("says why it could not save, keeping the values, without trying again", async () => {
    await renderEdit();
    const requests: string[] = [];
    server.use(
      http.patch("/feed/:id", ({ params }) => {
        requests.push(String(params.id));
        return HttpResponse.json({ error: "Internal server error" }, { status: 500 });
      }),
    );

    await replace("Titular", "El alquiler baja");
    await userEvent.click(saveButton());

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("No se pudo guardar la noticia");
    expect(alert).toHaveTextContent("Internal server error");
    expect(screen.getByLabelText("Titular")).toHaveValue("El alquiler baja");
    expect(requests).toHaveLength(1);
  });

  it("returns to the list when the feed was deleted meanwhile", async () => {
    const { feeds, router } = await renderEdit();
    await replace("Titular", "El alquiler baja");

    feeds.splice(0);
    await userEvent.click(saveButton());

    await waitFor(() => expect(router.state.location.pathname).toBe("/admin"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Esta noticia ya no existe");
  });
});

describe("a feed that does not exist", () => {
  it.each([
    ["an unknown id", crypto.randomUUID()],
    ["an id that is not a UUID", "nope"],
  ])("returns to the list for %s", async (_name, id) => {
    fakeAuth().signedIn();
    fakeFeedList([]);
    fakeFeedDetail([]);
    server.use(
      http.get("/feed/nope", () =>
        HttpResponse.json({ error: "id: Input should be a valid UUID" }, { status: 400 }),
      ),
    );
    const { router } = renderRoute(`/admin/feeds/${id}/edit`);

    await waitFor(() => expect(router.state.location.pathname).toBe("/admin"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Esta noticia ya no existe");
  });
});

describe("leaving", () => {
  it("asks first with unsaved changes, and stays when asked to", async () => {
    const { router } = await renderEdit();
    await userEvent.type(screen.getByLabelText("Titular"), "!");

    await userEvent.click(screen.getByRole("link", { name: "Cancelar" }));

    const dialog = await screen.findByRole("alertdialog", { name: "¿Salir sin guardar?" });
    expect(dialog).toHaveTextContent("Los cambios que no has guardado se perderán.");
    await userEvent.click(within(dialog).getByRole("button", { name: "Seguir editando" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(router.state.location.pathname).toMatch(/\/edit$/);
    expect(screen.getByLabelText("Titular")).toHaveValue("El alquiler sube por tercer trimestre!");
  });

  it("leaves when confirmed", async () => {
    const { router } = await renderEdit();
    await userEvent.type(screen.getByLabelText("Titular"), "!");

    await userEvent.click(screen.getByRole("link", { name: "Noticias" }));
    const dialog = await screen.findByRole("alertdialog", { name: "¿Salir sin guardar?" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Salir" }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/admin"));
  });

  it("does not ask without changes", async () => {
    const { router } = await renderEdit();

    await userEvent.click(screen.getByRole("link", { name: "Cancelar" }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/admin"));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("does not hold back the end of the session, and the form loads again afterwards", async () => {
    const { auth, api, router, feed } = await renderEdit(aScrapedFeed(), {
      token_expires_at: new Date(Date.now() + 1_000).toISOString(),
    });
    auth.accept(ADMIN);
    await userEvent.type(screen.getByLabelText("Titular"), "!");

    await waitFor(() => expect(router.state.location.pathname).toBe("/login"), {
      timeout: 3_000,
    });
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    await userEvent.type(await screen.findByLabelText("Email"), ADMIN.email);
    await userEvent.type(screen.getByLabelText("Contraseña"), ADMIN.password);
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() =>
      expect(router.state.location.pathname).toBe(`/admin/feeds/${feed.id}/edit`),
    );
    expect(await screen.findByLabelText("Titular")).toHaveValue(
      "El alquiler sube por tercer trimestre",
    );
    expect(api.reads).toEqual([feed.id, feed.id]);
  });
});

describe("deleting from the form", () => {
  it("returns to the list once deleted", async () => {
    const { deletes, router, feed } = await renderEdit();
    await userEvent.type(screen.getByLabelText("Titular"), "!");

    await userEvent.click(screen.getByRole("button", { name: "Borrar noticia" }));
    const dialog = screen.getByRole("alertdialog", { name: "¿Borrar esta noticia?" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Borrar" }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/admin"));
    expect(await screen.findByRole("status")).toHaveTextContent("Noticia borrada");
    expect(deletes.requests.map((request) => request.id)).toEqual([feed.id]);
    expect(screen.queryByRole("alertdialog", { name: "¿Salir sin guardar?" })).toBeNull();
  });
});

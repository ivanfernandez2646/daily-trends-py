import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw/http";
import { describe, expect, it } from "vitest";
import { fakeAuth } from "../test/fake-auth";
import { fakeFeedList } from "../test/fake-feed-list";
import { fakeCreateFeed } from "../test/fake-feed-writes";
import { renderRoute } from "../test/render";
import { server } from "../test/server";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

/** The create form of an administrator with a session, and the CMS list it returns to. */
async function renderNewFeed() {
  const token = fakeAuth().signedIn();
  fakeFeedList([]);
  const rendered = renderRoute("/admin/feeds/new");
  await screen.findByRole("heading", { level: 1, name: "Nueva noticia" });
  return { token, ...rendered };
}

async function fillIn({
  title = "El alquiler sube por tercer trimestre",
  description = "Madrid y Barcelona concentran las subidas.",
  author = "Laura Martín",
  category = "Economía",
} = {}) {
  await userEvent.type(screen.getByLabelText("Titular"), title);
  if (description !== "") {
    await userEvent.type(screen.getByLabelText("Entradilla (opcional)"), description);
  }
  await userEvent.type(screen.getByLabelText("Autor"), author);
  await userEvent.click(screen.getByRole("button", { name: category }));
}

function submit() {
  return userEvent.click(screen.getByRole("button", { name: "Crear noticia" }));
}

it("is reached from the CMS list", async () => {
  fakeAuth().signedIn();
  fakeFeedList([]);
  renderRoute("/admin");

  expect(await screen.findByRole("link", { name: "Nueva noticia" })).toHaveAttribute(
    "href",
    "/admin/feeds/new",
  );
});

it("asks for a title, an author and a category before sending anything", async () => {
  const creates = fakeCreateFeed();
  await renderNewFeed();

  await userEvent.type(screen.getByLabelText("Titular"), "   ");
  await submit();

  expect(screen.getByLabelText("Titular")).toHaveAccessibleDescription("Escribe un titular");
  expect(screen.getByLabelText("Autor")).toHaveAccessibleDescription("Escribe el autor");
  expect(screen.getByRole("group", { name: "Categoría" })).toHaveAccessibleDescription(
    "Elige una categoría",
  );
  expect(creates.requests).toEqual([]);
});

it("previews the feed as a front-page card while it is typed", async () => {
  await renderNewFeed();

  await fillIn();

  const preview = screen.getByRole("region", { name: "Así se verá en la portada" });
  expect(
    within(preview).getByRole("heading", { name: "El alquiler sube por tercer trimestre" }),
  ).toBeInTheDocument();
  expect(preview).toHaveTextContent("Madrid y Barcelona concentran las subidas.");
  expect(preview).toHaveTextContent("Economía");
  expect(preview).toHaveTextContent("Redacción · Laura Martín");
  expect(within(preview).queryByRole("link")).not.toBeInTheDocument();
});

it("creates the feed with a generated id and its trimmed values, then returns to the list", async () => {
  const creates = fakeCreateFeed();
  const { token, router } = await renderNewFeed();

  await fillIn({ title: "  El alquiler sube ", description: "" });
  await submit();

  await waitFor(() => expect(router.state.location.pathname).toBe("/admin"));
  expect(await screen.findByRole("status")).toHaveTextContent("Noticia creada");
  expect(creates.requests).toHaveLength(1);
  const [request] = creates.requests;
  expect(request?.id).toMatch(UUID);
  expect(request?.body).toEqual({
    title: "El alquiler sube",
    author: "Laura Martín",
    category: "ECONOMY",
  });
  expect(request?.authorization).toBe(`Bearer ${token}`);
});

it("keeps the values after a taken id, and tries again with another id", async () => {
  const creates = fakeCreateFeed({ taken: 1 });
  const { router } = await renderNewFeed();
  await fillIn();

  await submit();

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("No se pudo guardar la noticia");
  expect(alert).toHaveTextContent("already exists");
  expect(screen.getByLabelText("Titular")).toHaveValue("El alquiler sube por tercer trimestre");

  await submit();

  await waitFor(() => expect(router.state.location.pathname).toBe("/admin"));
  const [first, second] = creates.requests;
  expect(second?.id).toMatch(UUID);
  expect(second?.id).not.toBe(first?.id);
  expect(second?.body).toEqual(first?.body);
});

it("says why it could not save on an unexpected answer, without trying again", async () => {
  await renderNewFeed();
  const requests: string[] = [];
  server.use(
    http.put("/feed/:id", ({ params }) => {
      requests.push(String(params.id));
      return HttpResponse.json({ error: "Internal server error" }, { status: 500 });
    }),
  );
  await fillIn();

  await submit();

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("No se pudo guardar la noticia");
  expect(alert).toHaveTextContent("Internal server error");
  expect(requests).toHaveLength(1);
  expect(screen.getByLabelText("Autor")).toHaveValue("Laura Martín");
});

describe("leaving", () => {
  it("returns to the list with Cancelar", async () => {
    const { router } = await renderNewFeed();

    await userEvent.click(screen.getByRole("link", { name: "Cancelar" }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/admin"));
  });
});

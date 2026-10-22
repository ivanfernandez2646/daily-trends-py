import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw/http";
import { describe, expect, it } from "vitest";
import { api } from "../api/client";
import { TOKEN_KEY } from "../features/session/session";
import { fakeAuth } from "../test/fake-auth";
import { renderRoute } from "../test/render";
import { server } from "../test/server";

describe("without a session", () => {
  it("sends the user to log in, with the page to return to", async () => {
    fakeAuth();
    const { router } = renderRoute("/admin?q=madrid");

    await waitFor(() => expect(router.state.location.pathname).toBe("/login"));
    expect(router.state.location.search).toEqual({ redirect: "/admin?q=madrid" });
  });

  it("forgets a token the API rejects and sends the user to log in", async () => {
    fakeAuth();
    sessionStorage.setItem(TOKEN_KEY, "an-expired-token");
    const { router } = renderRoute("/admin");

    await waitFor(() => expect(router.state.location.pathname).toBe("/login"));
    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull();
  });
});

describe("with a session", () => {
  it("restores it with the stored token and shows the CMS layout", async () => {
    const auth = fakeAuth();
    const token = auth.signedIn({
      email: "editor@example.com",
      token_expires_at: "2099-10-21T16:05:00Z",
    });
    renderRoute("/admin");

    const menu = await screen.findByRole("complementary", { name: "Menú del CMS" });
    expect(within(menu).getByText("editor@example.com")).toBeInTheDocument();
    expect(within(menu).getByText("Sesión hasta las 18:05")).toBeInTheDocument();
    expect(within(menu).getByRole("link", { name: "Noticias" })).toHaveAttribute("href", "/admin");
    expect(within(menu).getByRole("link", { name: "Ver el sitio" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Noticias");
    expect(auth.authorizations).toEqual([`Bearer ${token}`]);
  });

  it("ends at the expiry of the token, sending the user to log in and back", async () => {
    const auth = fakeAuth();
    auth.signedIn({ token_expires_at: new Date(Date.now() + 300).toISOString() });
    const { router } = renderRoute("/admin?q=madrid");
    await screen.findByRole("complementary", { name: "Menú del CMS" });

    await waitFor(() => expect(router.state.location.pathname).toBe("/login"), {
      timeout: 2_000,
    });
    expect(router.state.location.search).toEqual({ redirect: "/admin?q=madrid" });
    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it("ends when the API rejects its token", async () => {
    fakeAuth().signedIn();
    server.use(
      http.get("/feed/scrap", () =>
        HttpResponse.json({ error: "Invalid or expired access token" }, { status: 401 }),
      ),
    );
    const { router } = renderRoute("/admin");
    await screen.findByRole("complementary", { name: "Menú del CMS" });

    // Any protected request of the session, as a write of the CMS would be.
    await api.GET("/feed/scrap");

    await waitFor(() => expect(router.state.location.pathname).toBe("/login"));
    expect(router.state.location.search).toEqual({ redirect: "/admin" });
    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it("logs out by forgetting the token and going to the front page", async () => {
    fakeAuth().signedIn();
    server.use(http.get("/feed/home", () => HttpResponse.json([])));
    const { router } = renderRoute("/admin");

    await userEvent.click(await screen.findByRole("button", { name: "Cerrar sesión" }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(await screen.findByRole("link", { name: "Acceder" })).toHaveAttribute("href", "/login");
  });
});

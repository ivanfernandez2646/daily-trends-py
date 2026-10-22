import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw/http";
import { describe, expect, it } from "vitest";
import { TOKEN_KEY } from "../features/session/session";
import { fakeAuth } from "../test/fake-auth";
import { renderRoute } from "../test/render";
import { server } from "../test/server";

const ADMIN = { email: "admin@example.com", password: "a-long-enough-secret" };

async function logIn(email: string, password: string) {
  const emailField = await screen.findByLabelText("Email");
  if (email !== "") {
    await userEvent.type(emailField, email);
  }
  if (password !== "") {
    await userEvent.type(screen.getByLabelText("Contraseña"), password);
  }
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
}

it("shows the login form", async () => {
  fakeAuth();
  renderRoute("/login");

  expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("Accede al CMS");
  expect(screen.getByLabelText("Email")).toHaveAttribute("type", "email");
  expect(screen.getByLabelText("Contraseña")).toHaveAttribute("type", "password");
});

describe("with wrong credentials", () => {
  it.each([
    ["an unknown email", "nobody@example.com", ADMIN.password],
    ["a wrong password", ADMIN.email, "not-the-password"],
  ])("answers the same for %s", async (_name, email, password) => {
    const auth = fakeAuth();
    auth.accept(ADMIN);
    renderRoute("/login");

    await logIn(email, password);

    expect(await screen.findByRole("alert")).toHaveTextContent("Email o contraseña incorrectos");
    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull();
  });
});

it("asks for both fields before asking the API", async () => {
  const auth = fakeAuth();
  renderRoute("/login");

  await logIn("", "");

  expect(await screen.findByText("Escribe tu email")).toBeInTheDocument();
  expect(screen.getByText("Escribe tu contraseña")).toBeInTheDocument();
  expect(screen.getByLabelText("Email")).toHaveAccessibleDescription("Escribe tu email");
  expect(auth.logins).toEqual([]);
});

it("sends the email without surrounding spaces", async () => {
  const auth = fakeAuth();
  auth.accept(ADMIN);
  renderRoute("/login");

  await logIn(`  ${ADMIN.email} `, ADMIN.password);

  await waitFor(() => expect(auth.logins).toEqual([ADMIN]));
});

it("says the login failed, with the API's reason, on an unexpected answer", async () => {
  fakeAuth();
  server.use(
    http.post("/auth/login", () =>
      HttpResponse.json({ error: "Internal server error" }, { status: 500 }),
    ),
  );
  renderRoute("/login");

  await logIn(ADMIN.email, ADMIN.password);

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("No se pudo iniciar sesión");
  expect(alert).toHaveTextContent("Internal server error");
});

describe("after logging in", () => {
  it("keeps the token in the tab's storage and goes to the CMS", async () => {
    const auth = fakeAuth();
    auth.accept(ADMIN);
    const { router } = renderRoute("/login");

    await logIn(ADMIN.email, ADMIN.password);

    await waitFor(() => expect(router.state.location.pathname).toBe("/admin"));
    expect(sessionStorage.getItem(TOKEN_KEY)).toMatch(/^token-/);
  });

  it("returns to the page it was given", async () => {
    const auth = fakeAuth();
    auth.accept(ADMIN);
    const { router } = renderRoute(`/login?redirect=${encodeURIComponent("/admin?q=madrid")}`);

    await logIn(ADMIN.email, ADMIN.password);

    await waitFor(() => expect(router.state.location.href).toBe("/admin?q=madrid"));
  });

  it.each([
    ["another site", "https://evil.example"],
    ["a protocol-relative address", "//evil.example"],
    ["a backslash address", "/\\evil.example"],
  ])("goes to the CMS instead of %s", async (_name, target) => {
    const auth = fakeAuth();
    auth.accept(ADMIN);
    const { router } = renderRoute(`/login?redirect=${encodeURIComponent(target)}`);

    await logIn(ADMIN.email, ADMIN.password);

    await waitFor(() => expect(router.state.location.href).toBe("/admin"));
  });
});

it("sends an administrator with a session to the CMS", async () => {
  fakeAuth().signedIn();
  const { router } = renderRoute("/login");

  await waitFor(() => expect(router.state.location.pathname).toBe("/admin"));
});

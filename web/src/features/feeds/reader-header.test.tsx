import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { renderWithRouter } from "../../test/render";
import { ReaderHeader } from "./reader-header";

describe("on the front page", () => {
  it("shows the masthead as the page's heading", async () => {
    renderWithRouter(<ReaderHeader variant="front" />);

    expect(
      await screen.findByRole("heading", { level: 1, name: "Daily Trends" }),
    ).toBeInTheDocument();
  });

  it("leads each section to the browse page with its category", async () => {
    renderWithRouter(<ReaderHeader variant="front" />);

    const sections = await screen.findByRole("navigation", { name: "Secciones" });
    expect(within(sections).getByRole("link", { name: "Portada" })).toHaveAttribute("href", "/");
    expect(within(sections).getByRole("link", { name: "Deportes" })).toHaveAttribute(
      "href",
      "/feeds?category=SPORTS",
    );
    expect(within(sections).getByRole("link", { name: "Todas las secciones" })).toHaveAttribute(
      "href",
      "/feeds",
    );
    expect(within(sections).getByRole("link", { name: "Buscar" })).toHaveAttribute(
      "href",
      "/feeds#buscar",
    );
  });

  it("names the six section shortcuts in order", async () => {
    renderWithRouter(<ReaderHeader variant="front" />);

    const shortcuts = await screen.findByRole("list", { name: "Secciones destacadas" });
    expect(
      within(shortcuts)
        .getAllByRole("link")
        .map((link) => link.textContent),
    ).toEqual([
      "Portada",
      "Política",
      "Internacional",
      "Economía",
      "Deportes",
      "Cultura",
      "Tecnología",
      "Todas las secciones",
    ]);
  });

  it("opens and closes the sections on a narrow screen", async () => {
    renderWithRouter(<ReaderHeader variant="front" />);

    const toggle = await screen.findByRole("button", { name: "Secciones" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("list", { name: "Todas las secciones" })).not.toBeInTheDocument();

    await userEvent.click(toggle);

    expect(toggle).toHaveAttribute("aria-expanded", "true");
    const all = screen.getByRole("list", { name: "Todas las secciones" });
    expect(within(all).getByRole("link", { name: "Salud" })).toHaveAttribute(
      "href",
      "/feeds?category=HEALTH",
    );

    await userEvent.click(toggle);

    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  it("opens the sections from the menu button too", async () => {
    renderWithRouter(<ReaderHeader variant="front" />);

    await userEvent.click(await screen.findByRole("button", { name: "Menú" }));

    expect(screen.getByRole("list", { name: "Todas las secciones" })).toBeInTheDocument();
  });

  it("says when the front page was updated", async () => {
    renderWithRouter(<ReaderHeader variant="front" updatedAt={new Date().toISOString()} />);

    expect(await screen.findByText("Actualizado ahora")).toBeInTheDocument();
  });
});

describe("on other pages", () => {
  it("shows the brand and the main navigation, without a page heading", async () => {
    renderWithRouter(<ReaderHeader variant="compact" />);

    const main = await screen.findByRole("navigation", { name: "Principal" });
    expect(within(main).getByRole("link", { name: "Portada" })).toHaveAttribute("href", "/");
    expect(within(main).getByRole("link", { name: "Explorar" })).toHaveAttribute("href", "/feeds");
    expect(screen.getByRole("link", { name: "Daily Trends" })).toHaveAttribute("href", "/");
    expect(screen.queryByRole("heading", { level: 1 })).not.toBeInTheDocument();
  });
});

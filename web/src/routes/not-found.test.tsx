import { screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { renderRoute } from "../test/render";

it("shows the not found page for an unknown address", async () => {
  renderRoute("/no-existe");

  expect(
    await screen.findByRole("heading", { level: 1, name: "No encontramos esta página." }),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Volver a la portada" })).toHaveAttribute("href", "/");
  expect(screen.getByRole("main")).toBeInTheDocument();
});

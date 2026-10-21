import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { Button, IconButton } from "./button";

it("is a button that does not submit forms unless asked", () => {
  render(<Button>Cargar más</Button>);

  expect(screen.getByRole("button", { name: "Cargar más" })).toHaveAttribute("type", "button");
});

it("calls its handler when clicked", async () => {
  let clicks = 0;
  render(<Button onClick={() => clicks++}>Reintentar</Button>);

  await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));

  expect(clicks).toBe(1);
});

it("cannot be used while disabled", () => {
  render(<Button disabled>Guardar cambios</Button>);

  expect(screen.getByRole("button", { name: "Guardar cambios" })).toBeDisabled();
});

it("states its variant", () => {
  render(<Button variant="destructive">Borrar</Button>);

  expect(screen.getByRole("button", { name: "Borrar" })).toHaveAttribute(
    "data-variant",
    "destructive",
  );
});

it("lends its look to a link", () => {
  render(
    <Button asChild variant="secondary">
      <a href="/feeds">Ver todas</a>
    </Button>,
  );

  const link = screen.getByRole("link", { name: "Ver todas" });
  expect(link).toHaveAttribute("data-variant", "secondary");
  expect(link).not.toHaveAttribute("type");
});

it("names an icon-only button with its label", () => {
  render(
    <IconButton label="Buscar">
      <svg />
    </IconButton>,
  );

  expect(screen.getByRole("button", { name: "Buscar" })).toBeInTheDocument();
});

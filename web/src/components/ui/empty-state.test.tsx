import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { Button } from "./button";
import { EmptyState } from "./empty-state";

it("shows its message and its one action", () => {
  render(
    <EmptyState message="No hay noticias de Deportes." action={<Button>Limpiar filtros</Button>} />,
  );

  expect(screen.getByText("No hay noticias de Deportes.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Limpiar filtros" })).toBeInTheDocument();
});

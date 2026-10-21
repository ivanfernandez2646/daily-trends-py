import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { Field } from "./field";

it("labels its input", () => {
  render(<Field label="Buscar noticias" type="search" />);

  expect(screen.getByRole("searchbox", { name: "Buscar noticias" })).toBeInTheDocument();
});

it("is valid without an error", () => {
  render(<Field label="Título" />);

  expect(screen.getByRole("textbox", { name: "Título" })).not.toHaveAttribute("aria-invalid");
});

it("links its error to the input", () => {
  render(<Field label="Título" error="El título es obligatorio" />);

  const input = screen.getByRole("textbox", { name: "Título" });
  expect(input).toHaveAttribute("aria-invalid", "true");
  expect(input).toHaveAccessibleDescription("El título es obligatorio");
});

import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { Field, TextareaField } from "./field";

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

it("labels a text area and links its error", () => {
  render(<TextareaField label="Entradilla" error="Demasiado larga" />);

  const area = screen.getByRole("textbox", { name: "Entradilla" });
  expect(area.tagName).toBe("TEXTAREA");
  expect(area).toHaveAttribute("aria-invalid", "true");
  expect(area).toHaveAccessibleDescription("Demasiado larga");
});

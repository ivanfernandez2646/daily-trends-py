import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { Notice } from "./notice";

it("announces an error as an alert", () => {
  render(<Notice tone="error">No se han podido cargar las noticias.</Notice>);

  expect(screen.getByRole("alert")).toHaveTextContent("No se han podido cargar las noticias.");
});

it("announces a success as a status", () => {
  render(<Notice tone="success">Noticia guardada.</Notice>);

  expect(screen.getByRole("status")).toHaveTextContent("Noticia guardada.");
});

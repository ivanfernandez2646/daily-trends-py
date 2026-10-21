import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { CategoryLabel } from "./category-label";

it("shows the Spanish label of the category", () => {
  const { container } = render(<CategoryLabel category="SPORTS" />);

  expect(screen.getByText("Deportes")).toBeInTheDocument();
  expect(container).toHaveTextContent(/^Deportes$/);
});

it("hides its color marker from assistive technology", () => {
  const { container } = render(<CategoryLabel category="SPORTS" />);

  expect(container.querySelector("[aria-hidden='true']")).not.toBeNull();
});

it("shows an unknown category as it comes", () => {
  render(<CategoryLabel category="TRAVEL" />);

  expect(screen.getByText("TRAVEL")).toBeInTheDocument();
});

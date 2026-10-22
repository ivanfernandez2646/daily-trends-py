import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { expect, it } from "vitest";
import type { FeedCategory } from "../../api/types";
import { CATEGORIES, categoryLabel } from "../../lib/labels";
import { CategoryPicker } from "./category-picker";

function Harness({ error }: { error?: string }) {
  const [category, setCategory] = useState<FeedCategory>();
  return <CategoryPicker category={category} onChange={setCategory} error={error} />;
}

it("offers every category, each with its marker, none chosen at first", () => {
  render(<Harness />);

  const group = screen.getByRole("group", { name: "Categoría" });
  const chips = within(group).getAllByRole("button");
  expect(chips.map((chip) => chip.textContent)).toEqual(CATEGORIES.map(categoryLabel));
  for (const chip of chips) {
    expect(chip).toHaveAttribute("aria-pressed", "false");
    expect(chip.querySelector("[aria-hidden='true']")).not.toBeNull();
  }
});

it("chooses one category at a time, and keeps it when pressed again", async () => {
  render(<Harness />);

  await userEvent.click(screen.getByRole("button", { name: "Deportes" }));
  await userEvent.click(screen.getByRole("button", { name: "Cultura" }));
  await userEvent.click(screen.getByRole("button", { name: "Cultura" }));

  expect(screen.getByRole("button", { name: "Cultura" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: "Deportes" })).toHaveAttribute("aria-pressed", "false");
});

it("links its error to the group", () => {
  render(<Harness error="Elige una categoría" />);

  expect(screen.getByRole("group", { name: "Categoría" })).toHaveAccessibleDescription(
    "Elige una categoría",
  );
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { Chip } from "./chip";

it("is a toggle button that is not pressed", () => {
  render(<Chip pressed={false}>Deportes</Chip>);

  expect(screen.getByRole("button", { name: "Deportes" })).toHaveAttribute("aria-pressed", "false");
});

it("states when it is pressed", () => {
  render(<Chip pressed>Deportes</Chip>);

  expect(screen.getByRole("button", { name: "Deportes" })).toHaveAttribute("aria-pressed", "true");
});

it("asks to be pressed when clicked", async () => {
  const changes: boolean[] = [];
  render(
    <Chip pressed={false} onPressedChange={(pressed) => changes.push(pressed)}>
      Deportes
    </Chip>,
  );

  await userEvent.click(screen.getByRole("button", { name: "Deportes" }));

  expect(changes).toEqual([true]);
});

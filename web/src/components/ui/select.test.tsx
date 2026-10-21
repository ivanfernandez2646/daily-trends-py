import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { Select } from "./select";

it("is a labelled native select", async () => {
  const picked: string[] = [];
  render(
    <Select label="Periódico" value="" onChange={(event) => picked.push(event.target.value)}>
      <option value="">Todos</option>
      <option value="EL_MUNDO">El Mundo</option>
    </Select>,
  );

  await userEvent.selectOptions(screen.getByRole("combobox", { name: "Periódico" }), "El Mundo");

  expect(picked).toEqual(["EL_MUNDO"]);
});

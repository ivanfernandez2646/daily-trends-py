import { screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { renderRoute } from "../test/render";

it("renders the front page with its main landmark and a single h1", async () => {
  renderRoute("/");

  const main = await screen.findByRole("main");
  expect(main).toBeInTheDocument();
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
});

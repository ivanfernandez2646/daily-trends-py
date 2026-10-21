import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { render } from "@testing-library/react";
import { createAppRouter } from "../router";

/** Render the whole app at `path`, with the real routes. */
export function renderRoute(path: string) {
  const router = createAppRouter(createMemoryHistory({ initialEntries: [path] }));
  return { router, ...render(<RouterProvider router={router} />) };
}

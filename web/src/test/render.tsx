import {
  createMemoryHistory,
  createRootRoute,
  createRouter,
  RouterProvider,
} from "@tanstack/react-router";
import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { createAppRouter } from "../router";

/** Render the whole app at `path`, with the real routes. */
export function renderRoute(path: string) {
  const router = createAppRouter(createMemoryHistory({ initialEntries: [path] }));
  return { router, ...render(<RouterProvider router={router} />) };
}

/** Render a component that holds links, inside a router of its own. */
export function renderWithRouter(ui: ReactNode) {
  const router = createRouter({
    routeTree: createRootRoute({ component: () => ui }),
    history: createMemoryHistory(),
  });
  return render(<RouterProvider router={router} />);
}

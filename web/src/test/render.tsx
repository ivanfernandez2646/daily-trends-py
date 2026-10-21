import {
  createMemoryHistory,
  createRootRoute,
  createRouter,
  RouterProvider,
} from "@tanstack/react-router";
import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { createQueryClient } from "../api/query-client";
import { createAppRouter } from "../router";

type RenderRouteOptions = { log?: (message: string) => void };

/** Render the whole app at `path`, with the real routes and a query client of its own. */
export function renderRoute(path: string, { log = () => {} }: RenderRouteOptions = {}) {
  const router = createAppRouter({
    queryClient: createQueryClient({ retryDelay: 0, log }),
    history: createMemoryHistory({ initialEntries: [path] }),
  });
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

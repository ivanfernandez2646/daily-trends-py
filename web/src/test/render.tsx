import {
  createMemoryHistory,
  createRootRoute,
  createRouter,
  RouterProvider,
} from "@tanstack/react-router";
import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { onTestFinished } from "vitest";
import { sendAccessToken } from "../api/client";
import { createQueryClient } from "../api/query-client";
import { createSession, type Session } from "../features/session/session";
import { SessionProvider } from "../features/session/session-context";
import { createAppRouter } from "../router";

type RenderRouteOptions = { log?: (message: string) => void };

/**
 * Render the whole app at `path`, with the real routes, a query client of its own and the session
 * of the token in `sessionStorage`, started as the app starts it.
 */
export function renderRoute(path: string, { log = () => {} }: RenderRouteOptions = {}) {
  const session = createSession({ storage: sessionStorage });
  onTestFinished(sendAccessToken(session));
  void session.restore();
  const router = createAppRouter({
    queryClient: createQueryClient({ retryDelay: 0, log }),
    session,
    history: createMemoryHistory({ initialEntries: [path] }),
  });
  return { router, session, ...render(<RouterProvider router={router} />) };
}

/** Render a component that holds links, inside a router of its own, with an anonymous session. */
export function renderWithRouter(
  ui: ReactNode,
  { session = createSession({ storage: sessionStorage }) }: { session?: Session } = {},
) {
  const router = createRouter({
    routeTree: createRootRoute({
      component: () => <SessionProvider session={session}>{ui}</SessionProvider>,
    }),
    history: createMemoryHistory(),
  });
  return render(<RouterProvider router={router} />);
}

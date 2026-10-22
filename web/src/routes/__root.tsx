import { createRootRouteWithContext, Outlet } from "@tanstack/react-router";
import { NotFoundPage } from "../features/feeds/not-found-page";
import type { Session } from "../features/session/session";

export type RouterContext = { session: Session };

export const Route = createRootRouteWithContext<RouterContext>()({
  component: Outlet,
  notFoundComponent: () => <NotFoundPage subject="página" />,
});

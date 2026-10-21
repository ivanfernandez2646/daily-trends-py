import { createRootRoute, Outlet } from "@tanstack/react-router";
import { NotFoundPage } from "../features/feeds/not-found-page";

export const Route = createRootRoute({
  component: Outlet,
  notFoundComponent: () => <NotFoundPage subject="página" />,
});

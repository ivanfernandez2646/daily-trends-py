import { type QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRouter, type RouterHistory } from "@tanstack/react-router";
import type { Session } from "./features/session/session";
import { SessionProvider } from "./features/session/session-context";
import { routeTree } from "./routeTree.gen";

type AppRouterOptions = { queryClient: QueryClient; session: Session; history?: RouterHistory };

export function createAppRouter({ queryClient, session, history }: AppRouterOptions) {
  return createRouter({
    routeTree,
    context: { session },
    ...(history && { history }),
    Wrap: ({ children }) => (
      <SessionProvider session={session}>
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </SessionProvider>
    ),
  });
}

declare module "@tanstack/react-router" {
  interface Register {
    router: ReturnType<typeof createAppRouter>;
  }
}

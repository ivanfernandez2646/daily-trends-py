import { QueryClientProvider, useQuery } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw/http";
import type { ReactNode } from "react";
import { expect, it } from "vitest";
import { server } from "../test/server";
import { api, unwrap } from "./client";
import { createQueryClient } from "./query-client";

function countedHome(status: number): { requests: () => number } {
  let requests = 0;
  server.use(
    http.get("/feed/home", () => {
      requests += 1;
      return HttpResponse.json({ error: `Answer ${status}` }, { status });
    }),
  );
  return { requests: () => requests };
}

function renderHomeQuery(log: (message: string) => void = () => {}) {
  const client = createQueryClient({ retryDelay: 0, log });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return renderHook(
    () => useQuery({ queryKey: ["home"], queryFn: () => unwrap(api.GET("/feed/home")) }),
    { wrapper },
  );
}

it("retries a failed read once", async () => {
  const home = countedHome(500);

  const { result } = renderHomeQuery();

  await waitFor(() => expect(result.current.isError).toBe(true));
  expect(home.requests()).toBe(2);
});

it("does not retry an answer that a retry cannot change", async () => {
  const home = countedHome(404);

  const { result } = renderHomeQuery();

  await waitFor(() => expect(result.current.isError).toBe(true));
  expect(home.requests()).toBe(1);
});

it("logs the API message once the read fails", async () => {
  countedHome(500);
  const logged: string[] = [];

  const { result } = renderHomeQuery((message) => logged.push(message));

  await waitFor(() => expect(result.current.isError).toBe(true));
  expect(logged).toEqual(["API 500: Answer 500"]);
});

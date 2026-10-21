import { QueryCache, QueryClient } from "@tanstack/react-query";
import { ApiError } from "./client";

type Log = (message: string, error: unknown) => void;

type QueryClientOptions = {
  /** Milliseconds before the one retry of a failed read. */
  retryDelay?: number;
  /** Where failed reads are reported: the reader shows its own message, never the API's. */
  log?: Log;
};

export function createQueryClient({
  retryDelay = 500,
  log = (message, error) => console.error(message, error),
}: QueryClientOptions = {}): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({ onError: (error) => log(describe(error), error) }),
    defaultOptions: {
      queries: {
        staleTime: 60_000,
        retry: (failureCount, error) => failureCount < 1 && !isClientError(error),
        retryDelay,
      },
    },
  });
}

/** A 4xx answer stays the same however often it is asked again. */
function isClientError(error: unknown): boolean {
  return error instanceof ApiError && error.status >= 400 && error.status < 500;
}

function describe(error: unknown): string {
  return error instanceof ApiError ? `API ${error.status}: ${error.message}` : String(error);
}

import createClient from "openapi-fetch";
import type { paths } from "./schema.gen";

export const api = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_BASE_URL || window.location.origin,
  // Looked up on every call, not kept from load time, so a fake network installed later is used.
  fetch: (request) => globalThis.fetch(request),
});

/** An answer of the API outside 2xx; `message` is the API's `error`, for logs only. */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type ApiResult<T> =
  | { data: T; error?: never; response: Response }
  | { data?: never; error: unknown; response: Response };

/** The body of a successful answer; any other answer throws an `ApiError`. */
export async function unwrap<T>(request: Promise<ApiResult<T>>): Promise<T> {
  const result = await request;
  if (result.data !== undefined) {
    return result.data;
  }
  throw new ApiError(result.response.status, errorMessage(result.error, result.response));
}

function errorMessage(error: unknown, response: Response): string {
  if (typeof error === "object" && error !== null && "error" in error) {
    const message = error.error;
    if (typeof message === "string") {
      return message;
    }
  }
  return response.statusText;
}

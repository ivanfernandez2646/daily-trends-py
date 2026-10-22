import createClient, { type Middleware } from "openapi-fetch";
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

type ApiResult = { data?: unknown; error?: unknown; response: Response };

/**
 * The body of a successful answer; any other answer throws an `ApiError`. Typed from the whole
 * result: inferring the body from its union would add the error side's `undefined`.
 */
export async function unwrap<R extends ApiResult>(
  request: Promise<R>,
): Promise<NonNullable<R["data"]>> {
  const result = await request;
  if (result.data !== undefined && result.data !== null) {
    return result.data;
  }
  throw new ApiError(result.response.status, errorMessage(result.error, result.response));
}

/** Resolve on a successful answer without a body, such as a 204; any other answer throws. */
export async function unwrapEmpty(request: Promise<ApiResult>): Promise<void> {
  const result = await request;
  if (!result.response.ok) {
    throw new ApiError(result.response.status, errorMessage(result.error, result.response));
  }
}

/** The part of the administrator's session that requests need. */
type AccessTokenHolder = { token(): string | undefined; end(reason: "expired"): void };

/**
 * Send the session's token as `Authorization: Bearer` while it is active, and end the session when
 * the API rejects that token. Answers the function that stops it.
 */
export function sendAccessToken(holder: AccessTokenHolder): () => void {
  const middleware: Middleware = {
    onRequest({ request }) {
      const token = holder.token();
      if (token !== undefined && !request.headers.has("Authorization")) {
        request.headers.set("Authorization", `Bearer ${token}`);
      }
      return request;
    },
    onResponse({ request, response }) {
      const token = holder.token();
      if (
        response.status === 401 &&
        token !== undefined &&
        request.headers.get("Authorization") === `Bearer ${token}`
      ) {
        holder.end("expired");
      }
      return response;
    },
  };
  api.use(middleware);
  return () => api.eject(middleware);
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

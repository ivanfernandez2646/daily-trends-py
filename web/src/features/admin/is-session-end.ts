import { ApiError } from "../../api/client";

/** A 401 ends the session and leads to the login page: no message of its own is needed. */
export function isSessionEnd(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

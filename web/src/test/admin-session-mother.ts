import type { AdminSessionResponse } from "../api/types";

/** `GET /auth/me` for a token valid for eight more hours; `overrides` state what a test cares about. */
export function anAdminSession(
  overrides: Partial<AdminSessionResponse> = {},
): AdminSessionResponse {
  return {
    id: crypto.randomUUID(),
    email: "admin@example.com",
    created_at: "2026-10-01T08:00:00Z",
    token_expires_at: new Date(Date.now() + 8 * 3_600_000).toISOString(),
    ...overrides,
  };
}

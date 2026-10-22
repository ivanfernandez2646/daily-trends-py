import { api, unwrap } from "./client";
import type { AdminSessionResponse } from "./types";

/** The access token of an administrator; wrong credentials throw a 401 `ApiError`. */
export async function logIn(email: string, password: string): Promise<string> {
  const { access_token } = await unwrap(api.POST("/auth/login", { body: { email, password } }));
  return access_token;
}

/** Who `token` belongs to and until when it is valid; a token the API rejects throws a 401. */
export function fetchAdminSession(token: string): Promise<AdminSessionResponse> {
  return unwrap(api.GET("/auth/me", { headers: { Authorization: `Bearer ${token}` } }));
}

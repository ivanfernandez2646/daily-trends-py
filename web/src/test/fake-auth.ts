import { HttpResponse, http } from "msw/http";
import type { components } from "../api/schema.gen";
import type { AdminSessionResponse } from "../api/types";
import { TOKEN_KEY } from "../features/session/session";
import { anAdminSession } from "./admin-session-mother";
import { server } from "./server";

type LoginRequest = components["schemas"]["LoginRequest"];
type Credentials = { email: string; password: string };

/**
 * A fake of `POST /auth/login` and `GET /auth/me` that answers like the API: `/auth/me` knows only
 * the tokens it issued, and any other token or none is a 401.
 */
export function fakeAuth() {
  const sessions = new Map<string, AdminSessionResponse>();
  const logins: LoginRequest[] = [];
  const authorizations: (string | null)[] = [];
  let accepted: Credentials | undefined;
  let acceptedSession: Partial<AdminSessionResponse> = {};

  function issue(overrides: Partial<AdminSessionResponse>): string {
    const token = `token-${crypto.randomUUID()}`;
    sessions.set(token, anAdminSession(overrides));
    return token;
  }

  server.use(
    http.get("/auth/me", ({ request }) => {
      const authorization = request.headers.get("Authorization");
      authorizations.push(authorization);
      const session = sessions.get(authorization?.replace(/^Bearer /, "") ?? "");
      return session !== undefined
        ? HttpResponse.json(session)
        : HttpResponse.json({ error: "Invalid or expired access token" }, { status: 401 });
    }),
    http.post("/auth/login", async ({ request }) => {
      const body = (await request.json()) as LoginRequest;
      logins.push(body);
      if (body.email !== accepted?.email || body.password !== accepted.password) {
        return HttpResponse.json({ error: "Invalid email or password" }, { status: 401 });
      }
      return HttpResponse.json({
        access_token: issue({ email: accepted.email, ...acceptedSession }),
        token_type: "bearer" as const,
        expires_in: 28_800,
      });
    }),
  );

  return {
    /** A stored token of a logged-in administrator, as after a reload. */
    signedIn(overrides: Partial<AdminSessionResponse> = {}): string {
      const token = issue(overrides);
      sessionStorage.setItem(TOKEN_KEY, token);
      return token;
    },
    /** Let `/auth/login` accept these credentials, issuing sessions like `overrides`. */
    accept(credentials: Credentials, overrides: Partial<AdminSessionResponse> = {}): void {
      accepted = credentials;
      acceptedSession = overrides;
    },
    /** Forget a token, as the API does once it expires. */
    revoke(token: string): void {
      sessions.delete(token);
    },
    logins,
    authorizations,
  };
}

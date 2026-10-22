import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../api/client";
import type { AdminSessionResponse } from "../../api/types";
import { anAdminSession } from "../../test/admin-session-mother";
import { createSession, type SessionEnd, TOKEN_KEY } from "./session";

const NOW = new Date("2026-10-21T10:00:00Z");
const HOUR = 3_600_000;

/** `GET /auth/me` as the session sees it: an answer per token, and the tokens it was asked for. */
function fakeAdminSessions(answers: Record<string, AdminSessionResponse | ApiError>) {
  const requests: string[] = [];
  const fetchAdmin = async (token: string) => {
    requests.push(token);
    const answer = answers[token] ?? new ApiError(401, "Invalid or expired access token");
    if (answer instanceof ApiError) {
      throw answer;
    }
    return answer;
  };
  return { fetchAdmin, requests };
}

function recordEnds(session: ReturnType<typeof createSession>) {
  const ends: SessionEnd[] = [];
  session.onEnd((reason) => ends.push(reason));
  return ends;
}

beforeEach(() => {
  vi.useFakeTimers({ now: NOW });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("restoring", () => {
  it("stays anonymous without asking the API when no token is stored", async () => {
    const api = fakeAdminSessions({});
    const session = createSession({ storage: sessionStorage, fetchAdmin: api.fetchAdmin });

    await session.restore();

    expect(session.state()).toEqual({ status: "anonymous" });
    expect(session.token()).toBeUndefined();
    expect(api.requests).toEqual([]);
  });

  it("activates the session of a stored token the API recognizes", async () => {
    sessionStorage.setItem(TOKEN_KEY, "a-token");
    const api = fakeAdminSessions({
      "a-token": anAdminSession({
        email: "admin@example.com",
        token_expires_at: "2026-10-21T18:00:00Z",
      }),
    });
    const session = createSession({ storage: sessionStorage, fetchAdmin: api.fetchAdmin });

    await session.restore();

    expect(session.state()).toEqual({
      status: "active",
      admin: { email: "admin@example.com", expiresAt: "2026-10-21T18:00:00Z" },
    });
    expect(session.token()).toBe("a-token");
  });

  it("is restoring while the API answers", async () => {
    sessionStorage.setItem(TOKEN_KEY, "a-token");
    const api = fakeAdminSessions({ "a-token": anAdminSession() });
    const session = createSession({ storage: sessionStorage, fetchAdmin: api.fetchAdmin });

    const restoring = session.restore();

    expect(session.state()).toEqual({ status: "restoring" });
    expect(session.token()).toBeUndefined();
    await restoring;
  });

  it("forgets a stored token the API rejects", async () => {
    sessionStorage.setItem(TOKEN_KEY, "an-expired-token");
    const api = fakeAdminSessions({});
    const session = createSession({ storage: sessionStorage, fetchAdmin: api.fetchAdmin });
    const ends = recordEnds(session);

    await session.restore();

    expect(session.state()).toEqual({ status: "anonymous" });
    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(ends).toEqual([]);
  });

  it("keeps the token for the next start when the API fails otherwise", async () => {
    sessionStorage.setItem(TOKEN_KEY, "a-token");
    const api = fakeAdminSessions({ "a-token": new ApiError(500, "Internal server error") });
    const session = createSession({ storage: sessionStorage, fetchAdmin: api.fetchAdmin });

    await session.restore();

    expect(session.state()).toEqual({ status: "anonymous" });
    expect(sessionStorage.getItem(TOKEN_KEY)).toBe("a-token");
  });

  it("asks the API once however often it is restored", async () => {
    sessionStorage.setItem(TOKEN_KEY, "a-token");
    const api = fakeAdminSessions({ "a-token": anAdminSession() });
    const session = createSession({ storage: sessionStorage, fetchAdmin: api.fetchAdmin });

    await Promise.all([session.restore(), session.restore()]);
    await session.restore();

    expect(api.requests).toEqual(["a-token"]);
  });
});

describe("starting", () => {
  it("stores the token and activates its session", async () => {
    const api = fakeAdminSessions({ "a-token": anAdminSession({ email: "admin@example.com" }) });
    const session = createSession({ storage: sessionStorage, fetchAdmin: api.fetchAdmin });
    await session.restore();

    await session.start("a-token");

    expect(sessionStorage.getItem(TOKEN_KEY)).toBe("a-token");
    expect(session.state()).toMatchObject({
      status: "active",
      admin: { email: "admin@example.com" },
    });
    await session.restore();
    expect(api.requests).toEqual(["a-token"]);
  });

  it("fails and forgets the token when the API does not answer who it belongs to", async () => {
    const api = fakeAdminSessions({ "a-token": new ApiError(500, "Internal server error") });
    const session = createSession({ storage: sessionStorage, fetchAdmin: api.fetchAdmin });

    await expect(session.start("a-token")).rejects.toThrow(ApiError);

    expect(session.state()).toEqual({ status: "anonymous" });
    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull();
  });
});

describe("ending", () => {
  async function activeSession(expiresAt: string) {
    const api = fakeAdminSessions({ "a-token": anAdminSession({ token_expires_at: expiresAt }) });
    const session = createSession({ storage: sessionStorage, fetchAdmin: api.fetchAdmin });
    await session.start("a-token");
    return session;
  }

  it("ends at the expiry of the token, not before", async () => {
    const session = await activeSession(new Date(NOW.getTime() + HOUR).toISOString());
    const ends = recordEnds(session);

    vi.advanceTimersByTime(HOUR - 1);
    expect(session.state().status).toBe("active");

    vi.advanceTimersByTime(1);
    expect(session.state()).toEqual({ status: "anonymous" });
    expect(session.token()).toBeUndefined();
    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(ends).toEqual(["expired"]);
  });

  it("ends at an expiry further away than one timer can wait", async () => {
    const days = 30;
    const session = await activeSession(new Date(NOW.getTime() + days * 24 * HOUR).toISOString());
    const ends = recordEnds(session);

    vi.advanceTimersByTime(25 * 24 * HOUR);
    expect(session.state().status).toBe("active");

    vi.advanceTimersByTime(5 * 24 * HOUR);
    expect(ends).toEqual(["expired"]);
  });

  it("logs out by forgetting the token, and does not expire afterwards", async () => {
    const session = await activeSession(new Date(NOW.getTime() + HOUR).toISOString());
    const ends = recordEnds(session);

    session.end("logout");
    vi.advanceTimersByTime(2 * HOUR);

    expect(session.state()).toEqual({ status: "anonymous" });
    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(ends).toEqual(["logout"]);
  });

  it("tells its subscribers about every change, with the same state in between", async () => {
    const api = fakeAdminSessions({ "a-token": anAdminSession() });
    const session = createSession({ storage: sessionStorage, fetchAdmin: api.fetchAdmin });
    const statuses: string[] = [];
    const unsubscribe = session.subscribe(() => statuses.push(session.state().status));

    await session.start("a-token");
    expect(session.state()).toBe(session.state());
    session.end("logout");
    unsubscribe();
    await session.start("a-token");

    expect(statuses).toEqual(["restoring", "active", "anonymous"]);
  });
});

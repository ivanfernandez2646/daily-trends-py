import { fetchAdminSession } from "../../api/auth";
import { ApiError } from "../../api/client";
import type { AdminSessionResponse } from "../../api/types";

export const TOKEN_KEY = "daily-trends.access-token";

// A longer delay makes `setTimeout` run at once.
const MAX_TIMER_DELAY = 2 ** 31 - 1;

export type Admin = { email: string; expiresAt: string };

export type SessionState =
  | { status: "anonymous" | "restoring"; admin?: never }
  | { status: "active"; admin: Admin };

export type SessionEnd = "logout" | "expired";

export type Session = {
  /** The same object until the session changes, as `useSyncExternalStore` needs. */
  state(): SessionState;
  /** The access token while the session is active. */
  token(): string | undefined;
  /** Restore the session of the stored token, once; a token the API rejects is forgotten. */
  restore(): Promise<void>;
  /** Keep a new token and activate its session; it fails, forgetting the token, when it can't. */
  start(token: string): Promise<void>;
  end(reason: SessionEnd): void;
  subscribe(listener: () => void): () => void;
  onEnd(listener: (reason: SessionEnd) => void): () => void;
};

type SessionOptions = {
  /** `sessionStorage` in the app: a reload keeps the token, closing the tab forgets it. */
  storage: Storage;
  fetchAdmin?: (token: string) => Promise<AdminSessionResponse>;
};

export function createSession({
  storage,
  fetchAdmin = fetchAdminSession,
}: SessionOptions): Session {
  let state: SessionState = { status: "anonymous" };
  let token: string | undefined;
  let restoring: Promise<void> | undefined;
  let expiry: ReturnType<typeof setTimeout> | undefined;
  const listeners = new Set<() => void>();
  const endListeners = new Set<(reason: SessionEnd) => void>();

  function change(next: SessionState) {
    state = next;
    for (const listener of listeners) {
      listener();
    }
  }

  function expireAt(instant: number) {
    expiry = setTimeout(
      () => (Date.now() >= instant ? end("expired") : expireAt(instant)),
      Math.min(instant - Date.now(), MAX_TIMER_DELAY),
    );
  }

  async function activate(candidate: string) {
    change({ status: "restoring" });
    try {
      const admin = await fetchAdmin(candidate);
      token = candidate;
      change({
        status: "active",
        admin: { email: admin.email, expiresAt: admin.token_expires_at },
      });
      expireAt(Date.parse(admin.token_expires_at));
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        storage.removeItem(TOKEN_KEY);
      }
      change({ status: "anonymous" });
      throw error;
    }
  }

  function end(reason: SessionEnd) {
    clearTimeout(expiry);
    token = undefined;
    storage.removeItem(TOKEN_KEY);
    restoring = Promise.resolve();
    change({ status: "anonymous" });
    for (const listener of endListeners) {
      listener(reason);
    }
  }

  return {
    state: () => state,
    token: () => token,
    restore() {
      if (restoring === undefined) {
        const stored = storage.getItem(TOKEN_KEY);
        // A session that cannot be restored is anonymous: the guard sends the user to log in.
        restoring = stored === null ? Promise.resolve() : activate(stored).catch(() => {});
      }
      return restoring;
    },
    async start(candidate) {
      clearTimeout(expiry);
      storage.setItem(TOKEN_KEY, candidate);
      const starting = activate(candidate);
      restoring = starting.catch(() => {});
      try {
        await starting;
      } catch (error) {
        storage.removeItem(TOKEN_KEY);
        throw error;
      }
    },
    end,
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    onEnd(listener) {
      endListeners.add(listener);
      return () => endListeners.delete(listener);
    },
  };
}

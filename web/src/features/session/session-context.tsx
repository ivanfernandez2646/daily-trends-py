import { createContext, type ReactNode, useContext, useSyncExternalStore } from "react";
import type { Session, SessionState } from "./session";

const SessionContext = createContext<Session | undefined>(undefined);

export function SessionProvider({ session, children }: { session: Session; children: ReactNode }) {
  return <SessionContext value={session}>{children}</SessionContext>;
}

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (session === undefined) {
    throw new Error("useSession needs a SessionProvider");
  }
  return session;
}

/** The session's state, rendering again whenever it changes. */
export function useSessionState(): SessionState {
  const session = useSession();
  return useSyncExternalStore(session.subscribe, session.state);
}

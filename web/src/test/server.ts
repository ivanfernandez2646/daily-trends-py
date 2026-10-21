import { setupServer } from "msw/node";

/** The fake API: each test describes the answers it needs with `server.use(...)`. */
export const server = setupServer();

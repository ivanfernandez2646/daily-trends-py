import "@fontsource-variable/inter";
// Optical size: the serif adapts its strokes from captions to the masthead.
import "@fontsource-variable/newsreader/opsz.css";
import "./styles/global.css";
import { RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { sendAccessToken } from "./api/client";
import { createQueryClient } from "./api/query-client";
import { createSession } from "./features/session/session";
import { createAppRouter } from "./router";

const root = document.getElementById("root");
if (root === null) {
  throw new Error("index.html has no #root element");
}

// Each tab logs in on its own, and a reload keeps the session.
const session = createSession({ storage: sessionStorage });
sendAccessToken(session);
void session.restore();

createRoot(root).render(
  <StrictMode>
    <RouterProvider router={createAppRouter({ queryClient: createQueryClient(), session })} />
  </StrictMode>,
);

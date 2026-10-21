import "@fontsource-variable/inter";
// Optical size: the serif adapts its strokes from captions to the masthead.
import "@fontsource-variable/newsreader/opsz.css";
import "./styles/global.css";
import { RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createQueryClient } from "./api/query-client";
import { createAppRouter } from "./router";

const root = document.getElementById("root");
if (root === null) {
  throw new Error("index.html has no #root element");
}

createRoot(root).render(
  <StrictMode>
    <RouterProvider router={createAppRouter({ queryClient: createQueryClient() })} />
  </StrictMode>,
);

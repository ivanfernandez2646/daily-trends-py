import type { components } from "../api/schema.gen";

type FeedResponse = components["schemas"]["FeedResponse"];

let sequence = 0;

/** A valid scraped feed as the API answers it; `overrides` state what a test cares about. */
export function aFeed(overrides: Partial<FeedResponse> = {}): FeedResponse {
  sequence += 1;
  return {
    id: crypto.randomUUID(),
    title: `Titular ${sequence}`,
    description: `Entradilla del titular ${sequence}`,
    author: "Redacción",
    source: "EL_MUNDO",
    category: "POLITICS",
    url: `https://www.elmundo.es/espana/noticia-${sequence}.html`,
    created_at: "2026-10-21T08:00:00Z",
    updated_at: null,
    ...overrides,
  };
}

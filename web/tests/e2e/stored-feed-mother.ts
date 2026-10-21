import type { FeedCategory, FeedSource } from "../../src/api/types";

/** A feed as the API stores it in the `feeds` collection. */
export type StoredFeed = {
  _id: string;
  title: string;
  description: string | null;
  author: string;
  source: FeedSource;
  category: FeedCategory;
  url: string | null;
  createdAt: Date;
  updatedAt: Date | null;
};

let sequence = 0;

export function aStoredFeed(overrides: Partial<StoredFeed> = {}): StoredFeed {
  sequence += 1;
  return {
    _id: crypto.randomUUID(),
    title: `Titular ${sequence}`,
    description: `Entradilla del titular ${sequence}`,
    author: "Redacción",
    source: "EL_MUNDO",
    category: "POLITICS",
    url: `https://www.elmundo.es/espana/noticia-${sequence}.html`,
    createdAt: new Date(),
    updatedAt: null,
    ...overrides,
  };
}

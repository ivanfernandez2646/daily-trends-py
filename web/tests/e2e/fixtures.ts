import { test as base } from "@playwright/test";
import { MongoClient } from "mongodb";
import { MONGO_URL } from "./environment";
import type { StoredFeed } from "./stored-feed-mother";

type Feeds = {
  /** Store feeds the way the API does; no test scrapes the real newspapers. */
  seed: (...feeds: StoredFeed[]) => Promise<void>;
};

export const test = base.extend<{ feeds: Feeds }>({
  // biome-ignore lint/correctness/noEmptyPattern: Playwright reads a fixture's dependencies from this pattern.
  feeds: async ({}, use) => {
    const client = new MongoClient(MONGO_URL);
    const collection = client.db().collection<StoredFeed>("feeds");
    await collection.deleteMany({});
    await use({
      seed: async (...feeds) => {
        await collection.insertMany(feeds);
      },
    });
    await client.close();
  },
});

export { expect } from "@playwright/test";

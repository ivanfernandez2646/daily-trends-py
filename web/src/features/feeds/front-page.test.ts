import { describe, expect, it } from "vitest";
import { aFeed } from "../../test/feed-mother";
import { lastUpdated, splitFrontPage } from "./front-page";

const feeds = (count: number) => Array.from({ length: count }, (_, index) => `feed ${index}`);

describe("splitFrontPage", () => {
  it("has nothing to show without feeds", () => {
    expect(splitFrontPage([])).toEqual({ lead: undefined, side: [], more: [] });
  });

  it("makes a single feed the lead alone", () => {
    expect(splitFrontPage(feeds(1))).toEqual({ lead: "feed 0", side: [], more: [] });
  });

  it("puts the next three feeds in the side column", () => {
    expect(splitFrontPage(feeds(4))).toEqual({
      lead: "feed 0",
      side: ["feed 1", "feed 2", "feed 3"],
      more: [],
    });
  });

  it("puts the rest under more headlines, in order", () => {
    const { more } = splitFrontPage(feeds(10));

    expect(more).toEqual(["feed 4", "feed 5", "feed 6", "feed 7", "feed 8", "feed 9"]);
  });
});

describe("lastUpdated", () => {
  it("is the newest creation date", () => {
    const newest = "2026-10-21T09:46:00Z";

    expect(
      lastUpdated([
        aFeed({ created_at: "2026-10-21T08:00:00Z" }),
        aFeed({ created_at: newest }),
        aFeed({ created_at: "2026-10-20T23:00:00Z" }),
      ]),
    ).toBe(newest);
  });

  it("is unknown without feeds", () => {
    expect(lastUpdated([])).toBeUndefined();
  });
});

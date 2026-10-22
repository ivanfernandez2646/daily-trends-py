import { screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { aFeed } from "../../test/feed-mother";
import { renderWithRouter } from "../../test/render";
import { FeedCard } from "./feed-card";

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-21T10:00:00Z"));
});

afterEach(() => {
  vi.useRealTimers();
});

const feed = aFeed({
  title: "El alquiler sube por tercer trimestre",
  description: "Madrid y Barcelona concentran las subidas.",
  author: "Laura Martín",
  source: "EL_ESPANOL",
  category: "ECONOMY",
  url: "https://www.elespanol.com/invertia/vivienda.html",
  created_at: "2026-10-21T09:00:00Z",
});

async function headline(level: number) {
  return screen.findByRole("heading", { level, name: feed.title });
}

describe("every variant", () => {
  it.each(["lead", "side", "grid", "row", "compact"] as const)(
    "%s links its headline to the feed's page and shows its category and newspaper",
    async (variant) => {
      renderWithRouter(<FeedCard feed={feed} variant={variant} />);

      const article = await screen.findByRole("article");
      expect(within(article).getByRole("link", { name: feed.title })).toHaveAttribute(
        "href",
        `/feeds/${feed.id}`,
      );
      expect(within(article).getByText("Economía")).toBeInTheDocument();
      expect(within(article).getByText("El Español")).toBeInTheDocument();
    },
  );
});

describe("lead", () => {
  it("shows the headline, the lead-in, the author, the time and the source link", async () => {
    renderWithRouter(<FeedCard feed={feed} variant="lead" />);

    expect(await headline(2)).toBeInTheDocument();
    expect(screen.getByText(feed.description ?? "")).toBeInTheDocument();
    expect(screen.getByText(/Laura Martín/)).toBeInTheDocument();
    expect(screen.getByText("hace 1 h")).toHaveAttribute("datetime", feed.created_at);
    expect(screen.getByRole("link", { name: /^Leer en El Español/ })).toHaveAttribute(
      "href",
      feed.url,
    );
  });

  it("has no source link for a feed without url", async () => {
    renderWithRouter(<FeedCard feed={{ ...feed, source: "CMS", url: null }} variant="lead" />);

    await headline(2);
    expect(screen.queryByRole("link", { name: /^Leer en/ })).not.toBeInTheDocument();
  });
});

describe("side", () => {
  it("shows the headline and the time, without the lead-in or the author", async () => {
    renderWithRouter(<FeedCard feed={feed} variant="side" />);

    expect(await headline(3)).toBeInTheDocument();
    expect(screen.getByText("hace 1 h")).toBeInTheDocument();
    expect(screen.queryByText(feed.description ?? "")).not.toBeInTheDocument();
    expect(screen.queryByText(/Laura Martín/)).not.toBeInTheDocument();
  });
});

describe("grid", () => {
  it("shows the description, the author and the time", async () => {
    renderWithRouter(<FeedCard feed={feed} variant="grid" />);

    expect(await headline(3)).toBeInTheDocument();
    expect(screen.getByText(feed.description ?? "")).toBeInTheDocument();
    expect(screen.getByText(/Laura Martín/)).toBeInTheDocument();
    expect(screen.getByText("hace 1 h")).toBeInTheDocument();
  });

  it("leaves the description out when the feed has none", async () => {
    renderWithRouter(<FeedCard feed={{ ...feed, description: null }} variant="grid" />);

    const article = await screen.findByRole("article");
    expect(article.querySelector("p")).toBeNull();
  });
});

describe("row", () => {
  it("shows the time column, the description and the author", async () => {
    renderWithRouter(<FeedCard feed={feed} variant="row" />);

    expect(await headline(2)).toBeInTheDocument();
    expect(screen.getByText("11:00")).toHaveAttribute("datetime", feed.created_at);
    expect(screen.getByText("Hoy")).toBeInTheDocument();
    expect(screen.getByText(feed.description ?? "")).toBeInTheDocument();
    expect(screen.getByText(/Laura Martín/)).toBeInTheDocument();
  });
});

describe("compact", () => {
  it("shows the headline and the time only", async () => {
    renderWithRouter(<FeedCard feed={feed} variant="compact" />);

    expect(await headline(2)).toBeInTheDocument();
    expect(screen.getByText("hace 1 h")).toBeInTheDocument();
    expect(screen.queryByText(feed.description ?? "")).not.toBeInTheDocument();
  });
});

it("takes the heading level of the page it is on", async () => {
  renderWithRouter(<FeedCard feed={feed} variant="grid" headingLevel={2} />);

  expect(await headline(2)).toBeInTheDocument();
});

it("shows the headline as text, without a link, when it is not linked", async () => {
  renderWithRouter(<FeedCard feed={feed} variant="grid" linked={false} />);

  expect(await screen.findByRole("heading", { level: 3, name: feed.title })).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: feed.title })).not.toBeInTheDocument();
});

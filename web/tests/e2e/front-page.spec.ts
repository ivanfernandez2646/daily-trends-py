import type { FeedSource } from "../../src/api/types";
import { expect, test } from "./fixtures";
import { aStoredFeed } from "./stored-feed-mother";

const SCRAPED: readonly FeedSource[] = [
  "EL_MUNDO",
  "EL_ESPANOL",
  "EL_CONFIDENCIAL",
  "LA_RAZON",
  "LA_VANGUARDIA",
];

test("the front page shows the newest feeds in the lead, the side column and the grid", async ({
  page,
  feeds,
}) => {
  const seeded = Array.from({ length: 10 }, (_, index) =>
    aStoredFeed({
      title: `Titular de portada ${index + 1}`,
      source: SCRAPED[index % SCRAPED.length],
      createdAt: new Date(Date.now() - (index + 1) * 60_000),
    }),
  );
  await feeds.seed(...seeded);
  const leaving: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).hostname !== "localhost") {
      leaving.push(request.url());
    }
  });

  await page.goto("/");

  const lead = page.getByRole("region", { name: "Destacadas" });
  await expect(lead.getByRole("heading", { level: 2 })).toHaveText("Titular de portada 1");
  await expect(lead.getByRole("heading", { level: 3 })).toHaveText([
    "Titular de portada 2",
    "Titular de portada 3",
    "Titular de portada 4",
  ]);
  await expect(
    page.getByRole("region", { name: "Más titulares" }).getByRole("heading", { level: 3 }),
  ).toHaveText(Array.from({ length: 6 }, (_, index) => `Titular de portada ${index + 5}`));

  const source = lead.getByRole("link", { name: /^Leer en El Mundo/ });
  await expect(source).toHaveAttribute("href", seeded[0]?.url ?? "");
  await expect(source).toHaveAttribute("target", "_blank");

  await page.getByRole("link", { name: "Titular de portada 2" }).click();
  await expect(page).toHaveURL(`/feeds/${seeded[1]?._id}`);

  expect(leaving).toEqual([]);
});

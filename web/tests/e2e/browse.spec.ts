import type { FeedCategory, FeedSource } from "../../src/api/types";
import { expect, test } from "./fixtures";
import { aStoredFeed } from "./stored-feed-mother";

const SOURCES: readonly FeedSource[] = ["EL_MUNDO", "LA_RAZON", "LA_VANGUARDIA", "CMS"];
const CATEGORIES: readonly FeedCategory[] = ["SPORTS", "POLITICS", "CULTURE"];

/** 25 feeds a minute apart, newest first, cycling through sources and categories. */
const seeded = Array.from({ length: 25 }, (_, index) => {
  const source = SOURCES[index % SOURCES.length] ?? "EL_MUNDO";
  return aStoredFeed({
    title: index % 5 === 0 ? `Las elecciones de ${index}` : `Noticia del día ${index}`,
    description: null,
    source,
    category: CATEGORIES[index % CATEGORIES.length] ?? "OTHER",
    url: source === "CMS" ? null : `https://example.com/${index}`,
    createdAt: new Date(Date.now() - (index + 1) * 60_000),
  });
});

const titles = (predicate: (index: number) => boolean) =>
  seeded.filter((_, index) => predicate(index)).map((feed) => feed.title);

test.beforeEach(async ({ feeds }) => {
  await feeds.seed(...seeded);
});

test("browsing loads the feeds newest first, a page at a time", async ({ page }) => {
  await page.goto("/feeds");
  const rows = page.getByRole("list", { name: "Noticias" }).getByRole("heading");

  await expect(rows).toHaveCount(20);
  await expect(rows.first()).toHaveText(seeded[0]?.title ?? "");

  await page.getByRole("button", { name: "Cargar más" }).click();

  await expect(rows).toHaveText(titles(() => true));
  await expect(page.getByRole("button", { name: "Cargar más" })).toHaveCount(0);
});

test("browsing filters by category, newspaper and words", async ({ page }) => {
  await page.goto("/feeds");
  const rows = page.getByRole("list", { name: "Noticias" }).getByRole("heading");
  await expect(rows).toHaveCount(20);

  await page.getByRole("button", { name: "Deportes" }).click();
  await expect(page).toHaveURL("/feeds?category=SPORTS");
  await expect(rows).toHaveText(titles((index) => index % 3 === 0));

  await page.getByRole("combobox", { name: "Periódico" }).selectOption({ label: "La Razón" });
  await expect(rows).toHaveText(titles((index) => index % 3 === 0 && index % 4 === 1));

  await page.getByRole("button", { name: "Limpiar filtros" }).click();
  await page.getByRole("searchbox", { name: "Buscar noticias" }).fill("elección");
  await expect(page).toHaveURL(/q=elecci/);
  await expect(rows).toHaveText(titles((index) => index % 5 === 0));
});

import { openAsAdmin } from "./admin";
import { expect, test } from "./fixtures";
import { aStoredFeed } from "./stored-feed-mother";

test("the CMS lists every feed and filters them by category", async ({ page, feeds }) => {
  await feeds.seed(
    aStoredFeed({ title: "Gol en el último minuto", category: "SPORTS" }),
    aStoredFeed({ title: "Récord en la maratón", category: "SPORTS", source: "CMS", url: null }),
    aStoredFeed({ title: "Los presupuestos llegan al Congreso", category: "POLITICS" }),
  );

  await openAsAdmin(page);
  const table = page.getByRole("table", { name: "Noticias" });
  await expect(table.getByRole("row")).toHaveCount(4);

  await page.getByRole("button", { name: "Deportes" }).click();

  await expect(page).toHaveURL("/admin?category=SPORTS");
  await expect(table.getByRole("row")).toHaveCount(3);
  await expect(table).not.toContainText("Los presupuestos llegan al Congreso");
});

test("deleting a feed from the CMS removes it from the reader", async ({ page, feeds }) => {
  const deleted = aStoredFeed({ title: "Una noticia que sobra", category: "CULTURE" });
  const kept = aStoredFeed({ title: "Una noticia que se queda", category: "CULTURE" });
  await feeds.seed(deleted, kept);

  await openAsAdmin(page);
  await page.getByRole("button", { name: `Borrar «${deleted.title}»` }).click();
  const dialog = page.getByRole("alertdialog", { name: "¿Borrar esta noticia?" });
  await expect(dialog).toContainText(deleted.title);
  await dialog.getByRole("button", { name: "Borrar" }).click();

  await expect(page.getByRole("status")).toContainText("Noticia borrada");
  const table = page.getByRole("table", { name: "Noticias" });
  await expect(table).not.toContainText(deleted.title);
  await expect(table).toContainText(kept.title);

  await page.goto("/feeds?category=CULTURE");
  await expect(page.getByRole("list", { name: "Noticias" })).toContainText(kept.title);
  await expect(page.getByRole("list", { name: "Noticias" })).not.toContainText(deleted.title);
});

test("the CMS fits a phone, scrolling the table inside its panel", async ({ page, feeds }) => {
  await feeds.seed(aStoredFeed({ title: "Un titular bastante largo para la tabla del CMS" }));
  await page.setViewportSize({ width: 360, height: 800 });

  await openAsAdmin(page);
  await expect(page.getByRole("table", { name: "Noticias" })).toBeVisible();

  const width = await page.evaluate(() => {
    const { scrollWidth, clientWidth } = document.documentElement;
    return { scrollWidth, clientWidth };
  });
  expect(width.scrollWidth).toBe(width.clientWidth);
});

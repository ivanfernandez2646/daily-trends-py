import { expect, test } from "./fixtures";
import { aStoredFeed } from "./stored-feed-mother";

test("the detail shows a feed and other feeds of its category", async ({ page, feeds }) => {
  const opened = aStoredFeed({
    title: "El alquiler sube por tercer trimestre",
    description: "Madrid y Barcelona concentran las subidas.",
    author: "Laura Martín",
    source: "EL_ESPANOL",
    category: "ECONOMY",
    url: "https://www.elespanol.com/invertia/vivienda/alquiler.html",
    createdAt: new Date(Date.now() - 60_000),
  });
  const sameCategory = [2, 3].map((minutes) =>
    aStoredFeed({
      title: `Más economía hace ${minutes} min`,
      category: "ECONOMY",
      createdAt: new Date(Date.now() - minutes * 60_000),
    }),
  );
  const otherCategory = aStoredFeed({ title: "Una noticia de deportes", category: "SPORTS" });
  await feeds.seed(opened, ...sameCategory, otherCategory);

  await page.goto("/");
  await page.getByRole("link", { name: opened.title }).click();

  await expect(page).toHaveURL(`/feeds/${opened._id}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(opened.title);
  await expect(page.getByText("Laura Martín")).toBeVisible();
  await expect(
    page
      .getByRole("region", { name: "Fuente original" })
      .getByRole("link", { name: /^Leer en El Español/ }),
  ).toHaveAttribute("href", opened.url ?? "");
  await expect(page.getByRole("region", { name: "Más de Economía" }).getByRole("link")).toHaveText(
    sameCategory.map((feed) => feed.title),
  );
});

for (const [name, path] of [
  ["an unknown feed", `/feeds/${crypto.randomUUID()}`],
  ["an id that is not a UUID", "/feeds/nope"],
  ["an unknown address", "/no-existe"],
] as const) {
  test(`${name} shows the not found page`, async ({ page }) => {
    await page.goto(path);

    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^No encontramos esta/);
    await page.getByRole("link", { name: "Volver a la portada" }).click();
    await expect(page).toHaveURL("/");
  });
}

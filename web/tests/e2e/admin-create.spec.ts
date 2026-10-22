import { openAsAdmin } from "./admin";
import { expect, test } from "./fixtures";

// Asking for `feeds` starts from an empty collection.
test("an administrator creates a feed and readers find it in its section", async ({
  page,
  feeds: _empty,
}) => {
  await openAsAdmin(page);
  await page.getByRole("link", { name: "Nueva noticia" }).click();
  await expect(page).toHaveURL("/admin/feeds/new");

  await page.getByLabel("Titular").fill("La biblioteca abre de noche");
  await page.getByLabel("Entradilla (opcional)").fill("Un horario nuevo para los estudiantes.");
  await page.getByLabel("Autor").fill("Ana Ruiz");
  await page.getByRole("button", { name: "Cultura" }).click();
  await expect(page.getByRole("region", { name: "Así se verá en la portada" })).toContainText(
    "La biblioteca abre de noche",
  );
  await page.getByRole("button", { name: "Crear noticia" }).click();

  await expect(page).toHaveURL("/admin");
  await expect(page.getByRole("status")).toContainText("Noticia creada");
  await expect(page.getByRole("table", { name: "Noticias" })).toContainText(
    "La biblioteca abre de noche",
  );

  await page.goto("/feeds?category=CULTURE");
  const list = page.getByRole("list", { name: "Noticias" });
  await expect(list).toContainText("La biblioteca abre de noche");
  await expect(list).toContainText("Redacción · Ana Ruiz");
});

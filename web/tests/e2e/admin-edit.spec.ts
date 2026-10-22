import { openAsAdmin } from "./admin";
import { expect, test } from "./fixtures";

// Asking for `feeds` starts from an empty collection.
test("an administrator edits a feed, readers see the change, and it is deleted", async ({
  page,
  feeds: _empty,
}) => {
  await openAsAdmin(page);
  await page.getByRole("link", { name: "Nueva noticia" }).click();
  await page.getByLabel("Titular").fill("El museo amplía su horario");
  await page.getByLabel("Autor").fill("Ana Ruiz");
  await page.getByRole("button", { name: "Cultura" }).click();
  await page.getByRole("button", { name: "Crear noticia" }).click();
  await expect(page).toHaveURL("/admin");

  await page.getByRole("link", { name: "Editar «El museo amplía su horario»" }).click();
  await expect(page.getByRole("group", { name: "No se puede cambiar" })).toContainText("Ana Ruiz");
  await page.getByLabel("Titular").fill("El museo abre también los lunes");
  await page.getByRole("button", { name: "Sociedad" }).click();
  await page.getByRole("button", { name: "Guardar cambios" }).click();

  await expect(page).toHaveURL("/admin");
  await expect(page.getByRole("region", { name: "Avisos" })).toContainText("Cambios guardados");
  await page.getByRole("link", { name: "El museo abre también los lunes", exact: true }).click();
  await expect(page).toHaveURL(/^[^?]*\/feeds\/[0-9a-f-]{36}$/);
  const detail = page.url();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "El museo abre también los lunes",
  );
  await expect(page.getByRole("link", { name: "Sociedad" })).toBeVisible();

  await page.goto(`${new URL(detail).pathname.replace("/feeds/", "/admin/feeds/")}/edit`);
  await page.getByRole("button", { name: "Borrar noticia" }).click();
  await page
    .getByRole("alertdialog", { name: "¿Borrar esta noticia?" })
    .getByRole("button", { name: "Borrar" })
    .click();

  await expect(page).toHaveURL("/admin");
  await expect(page.getByRole("region", { name: "Avisos" })).toContainText("Noticia borrada");
  await page.goto("/feeds?category=SOCIETY");
  await expect(page.getByText("No hay noticias en Sociedad.")).toBeVisible();
});

import { logIn } from "./admin";
import { expect, test } from "./fixtures";

test("wrong credentials are rejected without saying which one is wrong", async ({ page }) => {
  await page.goto("/login");

  await logIn(page, { password: "not-the-password" });

  await expect(page.getByRole("alert")).toHaveText("Email o contraseña incorrectos");
  await expect(page).toHaveURL("/login");
});

test("an administrator logs in, keeps the session on reload and logs out", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Acceder" }).click();

  await logIn(page);

  await expect(page).toHaveURL("/admin");
  await expect(page.getByRole("complementary", { name: "Menú del CMS" })).toContainText(
    "admin@example.com",
  );
  await page.reload();
  await expect(page.getByRole("button", { name: "Cerrar sesión" })).toBeVisible();

  await page.getByRole("button", { name: "Cerrar sesión" }).click();

  await expect(page).toHaveURL("/");
  await expect(page.getByRole("link", { name: "Acceder" })).toBeVisible();
});

test("the CMS without a session asks to log in and then returns", async ({ page }) => {
  await page.goto("/admin?q=madrid");

  await expect(page).toHaveURL(`/login?redirect=${encodeURIComponent("/admin?q=madrid")}`);
  await logIn(page);

  await expect(page).toHaveURL("/admin?q=madrid");
});

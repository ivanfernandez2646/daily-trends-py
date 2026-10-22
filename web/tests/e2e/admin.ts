import { expect, type Page } from "@playwright/test";
import { ADMIN_EMAIL, ADMIN_PASSWORD } from "./environment";

/** Fill the login form of the current page with the administrator's credentials, or others. */
export async function logIn(
  page: Page,
  { email = ADMIN_EMAIL, password = ADMIN_PASSWORD }: { email?: string; password?: string } = {},
) {
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Accede al CMS");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Contraseña").fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
}

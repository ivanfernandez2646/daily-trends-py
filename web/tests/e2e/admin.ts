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

/** Open a page of the CMS, logging in on the way as the administrator. */
export async function openAsAdmin(page: Page, path = "/admin") {
  await page.goto(path);
  await logIn(page);
  await expect(page).toHaveURL(path);
}

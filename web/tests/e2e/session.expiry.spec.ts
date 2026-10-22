import { logIn } from "./admin";
import { EXPIRY_TOKEN_TTL_SECONDS } from "./environment";
import { expect, test } from "./fixtures";

test("an expired session asks to log in again and returns to the page", async ({ page }) => {
  await page.goto("/admin?q=madrid");
  await logIn(page);
  await expect(page).toHaveURL("/admin?q=madrid");

  await expect(page).toHaveURL(/^[^?]*\/login\?/, {
    timeout: (EXPIRY_TOKEN_TTL_SECONDS + 5) * 1_000,
  });
  expect(new URL(page.url()).searchParams.get("redirect")).toBe("/admin?q=madrid");
  await logIn(page);

  await expect(page).toHaveURL("/admin?q=madrid");
  await expect(page.getByRole("button", { name: "Cerrar sesión" })).toBeVisible();
});

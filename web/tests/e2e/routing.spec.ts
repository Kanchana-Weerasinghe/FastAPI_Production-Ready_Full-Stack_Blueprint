import { expect, test } from "../fixtures/auth";

test.describe("Navigation & Auth Guards", () => {
  test("Unauthenticated user is redirected to the landing page", async ({
    page,
  }) => {
    await page.goto("/home");
    await expect(page).toHaveURL("/");
    await expect(
      page.getByRole("button", { name: "Sign in", exact: true }).first(),
    ).toBeVisible();
  });

  test("Authenticated user visiting landing page is redirected to home", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/.*\/home/);
  });

  test("User can use the Navbar to navigate between main sections", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/home");
    await expect(page).toHaveURL(/.*\/home/);
    await page.getByRole("link", { name: "Account", exact: true }).click();
    await expect(page).toHaveURL(/.*\/account/);
    await page.getByRole("link", { name: "Home", exact: true }).click();
    await expect(page).toHaveURL(/.*\/home/);
    await expect(
      page.getByRole("heading", { name: "Welcome to Boost" }),
    ).toBeVisible();
  });
});

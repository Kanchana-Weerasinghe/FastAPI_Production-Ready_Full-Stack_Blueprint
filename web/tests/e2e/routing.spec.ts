import { expect, test } from "../fixtures/auth";

test.describe("Navigation & Auth Guards", () => {
  test("Unauthenticated user is redirected to the landing page", async ({
    page,
  }) => {
    await page.goto("/todos");
    await expect(page).toHaveURL("/");
    await expect(
      page.getByRole("button", { name: "Sign in", exact: true }).first(),
    ).toBeVisible();
  });

  test("Authenticated user visiting landing page is redirected to todos", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/.*\/todos/);
  });

  test("User can use the Navbar to navigate between main sections", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/todos");
    await expect(page).toHaveURL(/.*\/todos/);
    await page.getByRole("link", { name: "Archive" }).click();
    await expect(page).toHaveURL(/.*\/archives/);
    await expect(
      page.getByPlaceholder("Search archived todos..."),
    ).toBeVisible();
    await page.getByRole("link", { name: "Attachments" }).click();
    await expect(page).toHaveURL(/.*\/attachments/);
    await expect(page.getByPlaceholder("Search files...")).toBeVisible();
    await page.getByRole("link", { name: "Todo" }).click();
    await expect(page).toHaveURL(/.*\/todos/);
  });
});

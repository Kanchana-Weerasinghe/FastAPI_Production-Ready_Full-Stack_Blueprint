import { expect, test } from "../fixtures/auth";

const API_URL = process.env.API_URL || "http://localhost:8000";

test.describe("Search & Pagination", () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    for (let i = 0; i < 9; i++) {
      await page.request.post(`${API_URL}/v2/todos/`, {
        data: { title: `Filler Todo ${i}` },
      });
    }
    await page.request.post(`${API_URL}/v2/todos/`, {
      data: { title: "Buy groceries" },
    });
    await page.request.post(`${API_URL}/v2/todos/`, {
      data: { title: "Read a book" },
    });

    await page.goto("/todos");
    await expect(
      page.getByRole("heading", { name: "Buy groceries" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Read a book" }),
    ).toBeVisible();
  });

  test("User can filter lists using the search bar", async ({
    authenticatedPage: page,
  }) => {
    await page.getByPlaceholder("Search todos...").fill("groceries");
    await expect(
      page.getByRole("heading", { name: "Buy groceries" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Read a book" }),
    ).not.toBeVisible();
    await page.getByPlaceholder("Search todos...").clear();
    await expect(
      page.getByRole("heading", { name: "Buy groceries" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Read a book" }),
    ).toBeVisible();
  });

  test("User can navigate between pages using pagination controls", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/todos");
    const page2Button = page.getByRole("button", { name: "2", exact: true });
    await expect(page2Button).toBeEnabled();
    await page2Button.click();
    const page1Button = page.getByRole("button", { name: "1", exact: true });
    await expect(page1Button).toBeEnabled();
  });
});

import { expect, test } from "../fixtures/auth";

test.describe("Archiving Workflow", () => {
  test("User can archive a todo from the dashboard", async ({
    seededTodo: { page, title },
  }) => {
    await page.goto("/todos");
    await expect(page).toHaveURL(/.*\/todos/);
    await expect(page.getByRole("heading", { name: title })).toBeVisible();
    await page.getByRole("button", { name: "Options" }).first().click();
    await page.getByRole("button", { name: "Delete" }).click();

    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible();
    await expect(
      modal.getByText(/This todo will be delete after a month of inactivity/i),
    ).toBeVisible();
    await modal.getByRole("button", { name: "Delete" }).click();

    await expect(page.getByText(/moved to archives/i)).toBeVisible();
    await expect(page).toHaveURL(/.*\/archives/);
    await expect(page.getByRole("heading", { name: title })).toBeVisible();
  });

  test("User can restore a todo from the archives", async ({
    archivedTodo: { page, title },
  }) => {
    await page.goto("/archives");
    await expect(page).toHaveURL(/.*\/archives/);
    await expect(page.getByRole("heading", { name: title })).toBeVisible();

    await page.getByRole("button", { name: "Options" }).first().click();
    await page.getByRole("button", { name: /restore/i }).click();

    await expect(page.getByText(/restored/i)).toBeVisible();
    await expect(page.getByRole("heading", { name: title })).toBeVisible();
  });

  test("User can permanently delete an item from the archives", async ({
    archivedTodo: { page, title },
  }) => {
    await page.goto("/archives");
    await expect(page).toHaveURL(/.*\/archives/);
    await expect(page.getByRole("heading", { name: title })).toBeVisible();

    await page.getByRole("button", { name: "Options" }).first().click();
    await page.getByRole("button", { name: /permanently delete/i }).click();

    const deleteModal = page.locator('[role="dialog"]');
    await expect(deleteModal).toBeVisible();
    await deleteModal.getByRole("button", { name: "Delete Forever" }).click();
    await expect(page.getByText(/deleted/i)).toBeVisible();
    await expect(page.getByText(title)).not.toBeVisible();
  });
});

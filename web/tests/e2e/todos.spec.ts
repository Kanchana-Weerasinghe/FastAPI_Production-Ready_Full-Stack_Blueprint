import { expect, test } from "../fixtures/auth";

test.describe("Todo Core Flow", () => {
  test("User can create a new todo and see it on the dashboard", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/todos");
    await page.getByRole("link", { name: "Add Todo" }).click();
    await expect(page).toHaveURL(/.*\/todo\/new/);
    const todoTitle = `E2E Test Todo ${Date.now()}`;
    await page.getByPlaceholder("Title").fill(todoTitle);
    await page
      .getByPlaceholder("Tell your story...")
      .fill("This is a test description");
    await page
      .getByRole("button", { name: "Create Todo", exact: true })
      .click();
    await expect(
      page.getByText("Todo created", { exact: false }),
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: todoTitle })).toBeVisible();
  });

  test("User can view full description of a todo on the detail page", async ({
    seededTodo: { page, title, description },
  }) => {
    await page.goto("/todos");
    await expect(page).toHaveURL(/.*\/todos/);
    await page.getByRole("heading", { name: title }).click();
    await expect(page).toHaveURL(/.*\/todo\/.+/);
    await expect(page.getByText(description)).toBeVisible();
  });

  test("User can edit a todo's text and save changes", async ({
    seededTodo: { page, title },
  }) => {
    await page.goto("/todos");
    await expect(page).toHaveURL(/.*\/todos/);
    await page.getByRole("heading", { name: title }).click();
    await page.getByRole("link", { name: "Edit" }).click();
    await expect(page).toHaveURL(/.*\/todo\/.+\/edit/);
    await page.getByPlaceholder("Tell your story...").clear();
    await page
      .getByPlaceholder("Tell your story...")
      .fill("Updated description");
    await page.getByRole("button", { name: "Save", exact: true }).click();
    await expect(page.getByText("Todo updated successfully")).toBeVisible();
    await page.getByRole("heading", { name: title }).click();
    await expect(page.getByText("Updated description")).toBeVisible();
  });

  test("User can toggle a todo's status to Completed", async ({
    seededTodo: { page, title },
  }) => {
    await page.goto("/todos");
    await expect(page).toHaveURL(/.*\/todos/);
    await expect(page.getByRole("heading", { name: title })).toBeVisible();

    await page.getByRole("button", { name: "Options" }).first().click();
    await expect(page.getByText("Mark as completed")).toBeVisible();
    await page.getByRole("button", { name: "Mark as completed" }).click();
    await page.getByRole("heading", { name: title }).click();
    await expect(page).toHaveURL(/.*\/todo\/.+/);
    await expect(page.getByText("Completed", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Mark as pending" }).click();
    await page.getByRole("heading", { name: title }).click();
    await expect(page).toHaveURL(/.*\/todo\/.+/);
    await expect(page.getByText("Pending", { exact: true })).toBeVisible();
  });
});

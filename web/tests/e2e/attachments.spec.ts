import path from "path";
import { fileURLToPath } from "url";

import { expect, test } from "../fixtures/auth";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe("Attachments Workflow", () => {
  test("User can attach a file while creating or editing a todo", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/todos");
    await page.getByRole("link", { name: "Add Todo" }).click();
    await page.getByPlaceholder("Title").fill("Todo with File");
    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: /add attachment/i }).click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(
      path.join(__dirname, "..", "fixtures", "test.json"),
    );
    await expect(page.getByText("test.json")).toBeVisible();
    await page
      .getByRole("button", { name: "Create Todo", exact: true })
      .click();
    await page.waitForURL(/.*\/todos/);
    await expect(page).toHaveURL(/.*\/todos/);
  });

  test("User can see all uploaded files in the global attachments view", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/todos");
    await page.getByRole("link", { name: "Add Todo" }).click();
    await page.getByPlaceholder("Title").fill("Another File Todo");
    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: /add attachment/i }).click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(
      path.join(__dirname, "..", "fixtures", "test.json"),
    );
    await page
      .getByRole("button", { name: "Create Todo", exact: true })
      .click();
    await page.waitForURL(/.*\/todos/);
    await expect(page).toHaveURL(/.*\/todos/);
    await page.getByRole("link", { name: "Attachments" }).click();
    await expect(page).toHaveURL(/.*\/attachments/);
    await expect(page.getByText("test.json")).toBeVisible();
  });

  test("User can download an attachment", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/todos");
    await page.getByRole("link", { name: "Add Todo" }).click();
    await page.getByPlaceholder("Title").fill("Todo for Download");
    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: /add attachment/i }).click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(
      path.join(__dirname, "..", "fixtures", "test.json"),
    );
    await page
      .getByRole("button", { name: "Create Todo", exact: true })
      .click();
    await page.waitForURL(/.*\/todos/);
    await expect(page).toHaveURL(/.*\/todos/);
    await page.getByRole("link", { name: "Attachments" }).click();
    await expect(page.getByText("test.json")).toBeVisible();
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download" }).first().click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe("test.json");
  });

  test("User can delete an attachment from the global list", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/todos");
    await page.getByRole("link", { name: "Add Todo" }).click();
    await page.getByPlaceholder("Title").fill("Todo for Delete");
    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: /add attachment/i }).click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(
      path.join(__dirname, "..", "fixtures", "test.json"),
    );
    await page
      .getByRole("button", { name: "Create Todo", exact: true })
      .click();
    await page.waitForURL(/.*\/todos/);
    await expect(page).toHaveURL(/.*\/todos/);
    await page.getByRole("link", { name: "Attachments" }).click();
    await expect(page).toHaveURL(/.*\/attachments/);
    await expect(page.getByText("test.json")).toBeVisible();
    await page.getByRole("button", { name: "Delete" }).first().click();
    await expect(page.getByText("test.json")).not.toBeVisible();
    await expect(page.getByText(/no attachments found/i)).toBeVisible();
  });
});

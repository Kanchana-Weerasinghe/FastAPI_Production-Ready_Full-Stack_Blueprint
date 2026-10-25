import { expect, test } from "../fixtures/auth";

test.describe("Sign Up Flow", () => {
  test("User can sign up successfully and is redirected to sign in", async ({
    page,
    freshAccount,
  }) => {
    await page.goto("/");
    await page
      .getByRole("button", { name: "Sign up", exact: true })
      .first()
      .click();
    await page.getByPlaceholder("you@example.com").fill(freshAccount.email);
    await page.getByPlaceholder("••••••••").fill(freshAccount.password);
    await page.locator('button[type="submit"]').click();
    await expect(page.getByText("Account created!")).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toHaveText(/Sign in/i);
  });

  test("User sees validation errors for invalid email/password formats", async ({
    page,
  }) => {
    await page.goto("/");
    await page
      .getByPlaceholder("you@example.com")
      .pressSequentially("invalid-email", { delay: 100 });
    await page.getByPlaceholder("••••••••").focus();
    await expect(
      page.getByText("Please enter a valid email address"),
    ).toBeVisible();
    await page.getByPlaceholder("••••••••").clear();
    await page
      .getByPlaceholder("••••••••")
      .pressSequentially("123", { delay: 100 });
    await page.getByPlaceholder("you@example.com").focus();
    await expect(
      page.getByText("Password must be at least 8 characters long"),
    ).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeDisabled();
  });
});

test.describe("Sign In Flow", () => {
  test("User can sign in with valid credentials and is redirected to /home", async ({
    page,
    seededAccount,
  }) => {
    await page.goto("/");
    await page.getByPlaceholder("you@example.com").fill(seededAccount.email);
    await page.getByPlaceholder("••••••••").fill(seededAccount.password);
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*\/home/);
    await expect(page.getByText("Welcome back!")).toBeVisible();
  });

  test("User receives an error toast for incorrect credentials", async ({
    page,
    seededAccount,
  }) => {
    await page.goto("/");
    await page.getByPlaceholder("you@example.com").fill(seededAccount.email);
    await page.getByPlaceholder("••••••••").fill("wrongpassword");
    await page.locator('button[type="submit"]').click();
    await expect(page.getByText("Authentication failed")).toBeVisible();
  });
});

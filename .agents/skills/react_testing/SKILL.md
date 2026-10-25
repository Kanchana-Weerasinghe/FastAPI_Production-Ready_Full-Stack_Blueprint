---
name: react-testing
description: Frontend testing standards using Vitest, React Testing Library, and Playwright. Use when writing UI tests.
---
# React Testing Skill

## Testing Tools

- Use `Vitest` as the primary test runner.
- Use `@testing-library/react` for component behavior testing.
- Use `Playwright` for all End-to-End (E2E) testing.

## Directory Structure

All test files are located under `web/tests/` and are organized as follows:

* `tests/unit/`: Contains unit tests testing components, hooks, features, and utils in isolation using Vitest and React Testing Library.
* `tests/e2e/`: Contains end-to-end integration tests that run in a browser using Playwright.
* `tests/mocks/`: Contains mocks for external integrations or APIs.
* `tests/fixtures/`: Contains reusable test fixtures or data.
* `tests/test_utils.tsx`: Contains common testing utilities, such as a custom `render` wrapper.

## Standards & Best Practices

- Test user interactions rather than implementation details.
- Ensure all tests are isolated and don't depend on global state.
- **No Comments Needed**: No need to add comments inside any of the test code (like `// Arrange`, `// Act`, `// Assert`). The `test` or `it` description strings are enough to explain the test logic.
- **Code Coverage**: **Ensure test coverage is strictly more than 80% of the lines.**
- **Mocking**: Use `vi.fn()` for mock functions and `vi.mock()` for module mocks in Vitest.

## Example: Unit Test (Vitest + Testing Library)

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Home } from "@/features/Home";

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}));
vi.mock("@/hooks/queries/user", () => ({
  useUser: () => ({ data: { email: "ada@example.com" } }),
}));

describe("Home", () => {
  it("greets the signed-in user", () => {
    render(<Home />);
    expect(
      screen.getByText("Signed in as ada@example.com"),
    ).toBeInTheDocument();
  });

  it("links to the account page", () => {
    render(<Home />);
    expect(
      screen.getByRole("link", { name: "Account security" }),
    ).toHaveAttribute("href", "/account");
  });
});
```

## Example: E2E Test (Playwright)

```typescript
import { expect, test } from "@playwright/test";

const API = process.env.API_URL || "http://localhost:8000";
const TEST_PASSWORD = "securepassword123";

test.describe("Sign Up Flow", () => {
  test.afterAll(async ({ request }, testInfo) => {
    const email = `e2e_signup_w${testInfo.workerIndex}@example.com`;
    const res = await request.post(`${API}/v1/auth/signin`, {
      data: { email, password: TEST_PASSWORD },
    });
    if (res.ok()) {
      await request.delete(`${API}/v2/user/me`);
    }
  });

  test("User can sign up successfully and is redirected to sign in", async ({
    page,
  }, testInfo) => {
    const email = `e2e_signup_w${testInfo.workerIndex}@example.com`;
    await page.goto("/");
    await page
      .getByRole("button", { name: "Sign up", exact: true })
      .first()
      .click();
    await page.getByPlaceholder("you@example.com").fill(email);
    await page.getByPlaceholder("••••••••").fill(TEST_PASSWORD);
    await page.locator('button[type="submit"]').click();
    await expect(page.getByText("Account created!")).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toHaveText(/Sign in/i);
  });
});
```

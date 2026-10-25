import { request, test as base } from "@playwright/test";

export interface AuthFixtures {
  authenticatedPage: import("@playwright/test").Page;
  freshAccount: { email: string; password: string };
  seededAccount: { email: string; password: string };
}

const API_URL = process.env.API_URL || "http://localhost:8000";

export const test = base.extend<AuthFixtures>({
  authenticatedPage: async ({ page }, use) => {
    const email = `e2e_${Date.now()}_${Math.random().toString(36).slice(2, 7)}@example.com`;
    const password = "securepassword123";
    const apiContext = await request.newContext({
      baseURL: API_URL,
    });
    await apiContext.post("/v1/auth/signup", {
      data: { email, password },
    });
    await apiContext.post("/v1/auth/signin", {
      data: { email, password },
    });
    const state = await apiContext.storageState();
    await page.context().addCookies(state.cookies);
    await use(page);
    await apiContext.delete("/v2/user/me");
    await apiContext.dispose();
  },

  freshAccount: async ({ playwright }, use) => {
    const email = `e2e_fresh_${Date.now()}_${Math.random().toString(36).slice(2, 7)}@example.com`;
    const password = "securepassword123";
    await use({ email, password });
    const apiContext = await playwright.request.newContext({
      baseURL: API_URL,
    });
    const res = await apiContext.post("/v1/auth/signin", {
      data: { email, password },
    });
    if (res.ok()) {
      await apiContext.delete("/v2/user/me");
    }
    await apiContext.dispose();
  },

  seededAccount: async ({ playwright }, use) => {
    const email = `e2e_seeded_${Date.now()}_${Math.random().toString(36).slice(2, 7)}@example.com`;
    const password = "securepassword123";
    const apiContext = await playwright.request.newContext({
      baseURL: API_URL,
    });
    await apiContext.post("/v1/auth/signup", {
      data: { email, password },
    });
    await use({ email, password });
    const res = await apiContext.post("/v1/auth/signin", {
      data: { email, password },
    });
    if (res.ok()) {
      await apiContext.delete("/v2/user/me");
    }
    await apiContext.dispose();
  },
});

export { expect } from "@playwright/test";

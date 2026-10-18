import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/**
 * Automated WCAG 2.1 AA checks (axe-core) on public pages. Automated tools find roughly a third of
 * accessibility issues; keyboard and screen-reader checks are still part of the review checklist.
 */
const PUBLIC_PAGES = [
  "/",
  "/forgot-password",
  "/reset-password?token=x".padEnd(40, "x"),
];

for (const path of PUBLIC_PAGES) {
  test(`has no WCAG 2.1 AA violations: ${path}`, async ({ page }) => {
    await page.goto(path);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  });
}

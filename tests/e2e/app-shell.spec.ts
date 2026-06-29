import { expect, test } from "@playwright/test";

test.describe("App Shell", () => {
  test("侧栏可见、主题切换、导航到画布列表", async ({ page }) => {
    await page.goto("/");

    const sidebar = page.getByTestId("app-sidebar");
    await expect(sidebar).toBeVisible();
    await expect(page.getByTestId("product-shell")).toBeVisible();
    await expect(page.getByRole("heading", { name: "AI Studio" })).toBeVisible();

    const themeToggle = page.getByTestId("theme-toggle");
    await themeToggle.click();
    await expect(page.locator("html")).toHaveClass(/dark/);

    await page.getByRole("link", { name: "无限画布" }).click();
    await expect(page).toHaveURL(/\/canvases$/);
    await expect(page.getByRole("heading", { name: "无限画布" })).toBeVisible();
  });
});

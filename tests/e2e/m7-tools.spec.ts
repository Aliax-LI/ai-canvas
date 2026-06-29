import { expect, test } from "@playwright/test";

test.describe("M7 tools pages", () => {
  test("文生图页加载", async ({ page }) => {
    await page.route("**/api/history?type=zimage", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });
    await page.goto("/tools/zimage");
    await expect(page.getByTestId("tool-zimage")).toBeVisible();
    await expect(page.getByRole("heading", { name: "文生图" })).toBeVisible();
  });

  test("在线生图页加载", async ({ page }) => {
    await page.route("**/api/config", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          image_models: ["gpt-image-2"],
          api_providers: [{ id: "comfly", name: "Comfly", primary: true, image_models: ["gpt-image-2"] }],
        }),
      });
    });
    await page.route("**/api/history?type=online", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });
    await page.goto("/tools/online");
    await expect(page.getByTestId("tool-online")).toBeVisible();
  });
});

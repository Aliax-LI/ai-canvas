import { expect, test } from "@playwright/test";

const MOCK_CANVAS = {
  id: "smart-1",
  title: "测试智能画布",
  icon: "sparkles",
  kind: "smart",
  nodes: [
    {
      id: "prompt_abc",
      type: "smart-prompt",
      x: 120,
      y: 100,
      w: 316,
      h: 240,
      title: "Prompt",
      text: "一只猫",
    },
  ],
  connections: [],
  viewport: { x: 0, y: 0, scale: 1 },
  logs: [],
  settings: {},
  updated_at: Date.now(),
};

test.describe("M8 smart canvas", () => {
  test("智能画布页加载与添加提示词卡片", async ({ page }) => {
    let savedBody: Record<string, unknown> | null = null;

    await page.route("**/api/canvases/smart-1", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ canvas: MOCK_CANVAS }),
        });
        return;
      }
      if (route.request().method() === "PUT") {
        savedBody = route.request().postDataJSON() as Record<string, unknown>;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            canvas: {
              ...MOCK_CANVAS,
              nodes: savedBody.nodes,
              title: savedBody.title,
              updated_at: Date.now(),
            },
          }),
        });
        return;
      }
      await route.continue();
    });

    await page.goto("/smart/smart-1");
    await expect(page.getByTestId("smart-canvas-page")).toBeVisible();
    await expect(page.getByTestId("smart-canvas-viewport")).toBeVisible();
    await expect(page.getByText("一只猫")).toBeVisible();

    await page.getByTestId("smart-create-fab").click();
    await expect(page.getByTestId("smart-create-menu")).toBeVisible();
    await page.getByTestId("smart-create-prompt").click();

    await expect(page.getByTestId("smart-card-prompt_abc")).toBeVisible();
    const cards = page.locator("article[data-testid^='smart-card-']");
    await expect(cards).toHaveCount(2);

    await page.getByTestId("smart-delete-selected").click();
    await expect(cards).toHaveCount(1);
  });
});

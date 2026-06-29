import { expect, test } from "@playwright/test";

const MOCK_CANVAS = {
  id: "canvas-1",
  title: "测试无限画布",
  icon: "layout",
  kind: "canvas",
  nodes: [
    {
      id: "prompt_abc",
      type: "prompt",
      x: 120,
      y: 100,
      text: "一只猫在草地上",
    },
    {
      id: "img_def",
      type: "image",
      x: 400,
      y: 100,
      url: "",
      name: "空白图片",
    },
  ],
  connections: [{ id: "c1", from: "prompt_abc", to: "img_def" }],
  viewport: { x: 0, y: 0, scale: 1 },
  logs: [],
  settings: {},
  updated_at: Date.now(),
};

test.describe("M9 canvas editor", () => {
  test("无限画布页加载 shell 与 xyflow 渲染", async ({ page }) => {
    await page.route("**/api/canvases/canvas-1", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ canvas: MOCK_CANVAS }),
        });
        return;
      }
      if (route.request().method() === "PUT") {
        const savedBody = route.request().postDataJSON() as Record<string, unknown>;
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

    await page.goto("/canvas/canvas-1");
    await expect(page.getByTestId("canvas-shell")).toBeVisible();
    await expect(page.getByTestId("canvas-editor-page")).toBeVisible();
    await expect(page.getByTestId("canvas-editor-viewport")).toBeVisible();
    await expect(page.getByTestId("canvas-flow")).toBeVisible();
    await expect(page.getByTestId("canvas-node-prompt_abc")).toBeVisible();
    await expect(page.getByText("一只猫在草地上")).toBeVisible();

    await page.getByTestId("canvas-create-fab").click();
    await expect(page.getByTestId("canvas-create-menu")).toBeVisible();
    await page.getByTestId("canvas-create-output").click();

    const outputNodes = page.locator("[data-testid^='canvas-node-']");
    await expect(outputNodes).toHaveCount(3);
  });
});

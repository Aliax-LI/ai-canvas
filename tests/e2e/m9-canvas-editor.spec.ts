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
    {
      id: "legacy_unknown",
      type: "customLegacyType",
      x: 700,
      y: 100,
      foo: "bar",
      count: 2,
    },
  ],
  connections: [{ id: "c1", from: "prompt_abc", to: "img_def" }],
  viewport: { x: 0, y: 0, scale: 1 },
  logs: [],
  settings: {},
  updated_at: Date.now(),
};

const MOCK_CANVAS_WITH_GENERATOR = {
  id: "canvas-2",
  title: "生成器连线测试",
  icon: "layout",
  kind: "canvas",
  nodes: [
    {
      id: "prompt_run",
      type: "prompt",
      x: 80,
      y: 200,
      text: "夕阳下的山脉",
    },
    {
      id: "gen_run",
      type: "generator",
      x: 400,
      y: 200,
      apiProvider: "comfly",
      model: "dall-e-3",
      ratio: "square",
      resolution: "1k",
      inputs: ["prompt_run"],
    },
  ],
  connections: [{ id: "c_prompt_gen", from: "prompt_run", to: "gen_run" }],
  viewport: { x: 0, y: 0, scale: 1 },
  logs: [],
  settings: {},
  updated_at: Date.now(),
};

const MOCK_CANVAS_CASCADE_CHAIN = {
  id: "canvas-3",
  title: "级联链测试",
  icon: "layout",
  kind: "canvas",
  nodes: [
    {
      id: "prompt_cascade",
      type: "prompt",
      x: 80,
      y: 200,
      text: "森林中的小径",
    },
    {
      id: "gen_cascade",
      type: "generator",
      x: 360,
      y: 200,
      apiProvider: "comfly",
      model: "dall-e-3",
      ratio: "square",
      resolution: "1k",
      inputs: ["prompt_cascade"],
    },
    {
      id: "out_cascade",
      type: "output",
      x: 640,
      y: 200,
      images: [],
    },
  ],
  connections: [
    { id: "c1", from: "prompt_cascade", to: "gen_cascade" },
    { id: "c2", from: "gen_cascade", to: "out_cascade" },
  ],
  viewport: { x: 0, y: 0, scale: 1 },
  logs: [],
  settings: {},
  updated_at: Date.now(),
};

const MOCK_ASSET_LIBRARY = {
  library: {
    libraries: [
      {
        id: "lib1",
        name: "默认库",
        type: "default",
        categories: [
          {
            id: "cat1",
            name: "图片",
            type: "image",
            items: [
              {
                id: "asset1",
                name: "测试图",
                url: "/uploads/test.png",
              },
            ],
          },
        ],
      },
    ],
    active_library_id: "lib1",
  },
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
    await expect(page.getByText("未知节点 · customLegacyType")).toBeVisible();

    await page.getByTestId("canvas-create-fab").click();
    await expect(page.getByTestId("canvas-create-menu")).toBeVisible();
    await expect(page.getByTestId("canvas-create-msgen")).toBeVisible();
    await expect(page.getByTestId("canvas-create-comfy")).toBeVisible();
    await expect(page.getByTestId("canvas-create-video")).toBeVisible();
    await expect(page.getByTestId("canvas-create-llm")).toBeVisible();
    await page.getByTestId("canvas-create-output").click();

    const outputNodes = page.locator("[data-testid^='canvas-node-']");
    await expect(outputNodes).toHaveCount(4);
  });

  test("Batch 3：日志面板与 generator 上游 prompt 预览", async ({ page }) => {
    await page.route("**/api/canvases/canvas-2", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ canvas: MOCK_CANVAS_WITH_GENERATOR }),
        });
        return;
      }
      await route.continue();
    });

    await page.goto("/canvas/canvas-2");
    await expect(page.getByTestId("canvas-node-gen_run")).toBeVisible();
    await expect(page.getByTestId("canvas-generator-prompt-preview")).toHaveText("夕阳下的山脉");

    await page.getByTestId("canvas-logs-toggle").click();
    await expect(page.getByTestId("canvas-logs-panel")).toBeVisible();
    await expect(page.getByText("生成日志")).toBeVisible();
  });

  test("Batch 4：级联按钮、资产库侧栏与撤销", async ({ page }) => {
    await page.route("**/api/canvases/canvas-3", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ canvas: MOCK_CANVAS_CASCADE_CHAIN }),
        });
        return;
      }
      if (route.request().method() === "PUT") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            canvas: { ...MOCK_CANVAS_CASCADE_CHAIN, updated_at: Date.now() },
          }),
        });
        return;
      }
      await route.continue();
    });

    await page.route("**/api/asset-library", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(MOCK_ASSET_LIBRARY),
        });
        return;
      }
      await route.continue();
    });

    await page.goto("/canvas/canvas-3");
    await expect(page.getByTestId("canvas-node-gen_cascade")).toBeVisible();
    await expect(page.getByTestId("canvas-cascade-run")).toBeVisible();
    await expect(page.getByTestId("canvas-cascade-run-gen_cascade")).toBeVisible();

    await page.getByTestId("canvas-assets-toggle").click();
    await expect(page.getByTestId("canvas-assets-sidebar")).toBeVisible();
    await expect(page.getByTestId("canvas-asset-item-asset1")).toBeVisible();

    const beforeCount = await page.locator("[data-testid^='canvas-node-']").count();
    await page.getByTestId("canvas-create-fab").click();
    await page.getByTestId("canvas-create-prompt").click();
    await expect(page.locator("[data-testid^='canvas-node-']")).toHaveCount(beforeCount + 1);

    await page.keyboard.press("ControlOrMeta+z");
    await expect(page.locator("[data-testid^='canvas-node-']")).toHaveCount(beforeCount);
  });

  test("Batch 5：工作流导出与任务恢复", async ({ page }) => {
    await page.route("**/api/canvases/canvas-4", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            canvas: {
              ...MOCK_CANVAS,
              id: "canvas-4",
              title: "Batch5 测试",
              nodes: [
                ...MOCK_CANVAS.nodes,
                {
                  id: "ltx_test",
                  type: "ltxDirector",
                  x: 200,
                  y: 400,
                  globalPrompt: "测试 LTX",
                  durationSeconds: 5,
                  frameRate: 24,
                  durationFrames: 120,
                  ltxTimelineData: "",
                  ltxSegments: [],
                  inputs: [],
                },
              ],
            },
          }),
        });
        return;
      }
      await route.continue();
    });

    await page.goto("/canvas/canvas-4");
    await expect(page.getByTestId("canvas-workflow-export")).toBeVisible();
    await expect(page.getByTestId("canvas-workflow-import")).toBeVisible();
    await expect(page.getByTestId("canvas-task-recovery")).toBeVisible();
    await expect(page.getByTestId("canvas-ltx-timeline-ltx_test")).toBeVisible();

    await page.getByTestId("canvas-task-recovery").click();
    await expect(page.getByRole("heading", { name: "任务恢复" })).toBeVisible();
    await page.keyboard.press("Escape");

    await page.getByTestId("canvas-create-fab").click();
    await page.getByTestId("canvas-create-ltxDirector").click();
    await expect(page.locator("[data-testid^='canvas-ltx-timeline-']")).toHaveCount(2);
  });
});

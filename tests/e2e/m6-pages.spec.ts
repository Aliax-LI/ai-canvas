import { expect, test } from "@playwright/test";

test.describe("M6 pages", () => {
  test("画布列表页加载", async ({ page }) => {
    await page.route("**/api/projects", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ projects: [{ id: "default", name: "默认项目" }] }),
      });
    });
    await page.route("**/api/canvases", async (route) => {
      if (route.request().url().includes("/trash")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ canvases: [], retention_days: 30 }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          canvases: [
            {
              id: "c1",
              title: "测试画布",
              icon: "🧩",
              kind: "classic",
              project: "default",
              updated_at: Date.now(),
              created_at: Date.now(),
              node_count: 3,
            },
          ],
        }),
      });
    });

    await page.goto("/canvases");
    await expect(page.getByTestId("canvas-list-page")).toBeVisible();
    await expect(page.getByText("测试画布")).toBeVisible();
  });

  test("GPT 对话页加载", async ({ page }) => {
    await page.route("**/api/config", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          chat_models: ["gpt-5.5"],
          image_models: [],
          video_models: [],
          api_providers: [{ id: "comfly", name: "Comfly", primary: true, chat_models: ["gpt-5.5"] }],
        }),
      });
    });
    await page.route("**/api/conversations", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user_id: "local",
          conversations: [{ id: "conv1", title: "你好", updated_at: 1, created_at: 1, last_message: "hi" }],
        }),
      });
    });
    await page.route("**/api/conversations/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          conversation: { id: "conv1", title: "你好", messages: [], created_at: 1, updated_at: 1 },
        }),
      });
    });

    await page.goto("/chat");
    await expect(page.getByTestId("chat-page")).toBeVisible();
    await expect(page.getByText("你好")).toBeVisible();
  });

  test("素材库页加载", async ({ page }) => {
    await page.route("**/api/asset-library", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          library: {
            active_library_id: "lib1",
            libraries: [
              {
                id: "lib1",
                name: "默认库",
                type: "asset",
                categories: [
                  {
                    id: "cat1",
                    name: "默认分组",
                    type: "image",
                    items: [{ id: "a1", name: "sample.png", url: "/assets/sample.png", kind: "image" }],
                  },
                ],
              },
            ],
          },
        }),
      });
    });

    await page.goto("/assets");
    await expect(page.getByTestId("assets-page")).toBeVisible();
    await expect(page.getByText("sample.png")).toBeVisible();
  });
});

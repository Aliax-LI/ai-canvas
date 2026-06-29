import { expect, test } from "@playwright/test";

const mockProvider = {
  id: "comfly",
  name: "Comfly",
  base_url: "https://api.example.com/v1",
  protocol: "openai",
  image_request_mode: "openai",
  enabled: true,
  primary: true,
  image_models: ["gpt-image-2"],
  chat_models: ["gpt-5.5"],
  video_models: [],
  has_key: false,
};

test.describe("Settings pages", () => {
  test("API 设置页加载并显示平台列表", async ({ page }) => {
    await page.route("**/api/providers", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ providers: [mockProvider] }),
      });
    });

    await page.goto("/settings/api");
    await expect(page.getByTestId("settings-page")).toBeVisible();
    await expect(page.getByRole("heading", { name: "API 设置" })).toBeVisible();
    await expect(page.getByTestId("provider-list")).toBeVisible();
    await expect(page.getByTestId("provider-editor")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Comfly", level: 2 })).toBeVisible();
  });

  test("ComfyUI 设置页加载工作流侧栏", async ({ page }) => {
    await page.route("**/api/comfyui/instances", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ instances: ["127.0.0.1:8188"] }),
      });
    });
    await page.route("**/api/workflows", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          workflows: [{ name: "Z-Image.json", title: "Z-Image", builtin: true, field_count: 2 }],
        }),
      });
    });
    await page.route("**/api/workflows/**", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            name: "Z-Image.json",
            workflow: {},
            config: { title: "Z-Image", fields: [] },
            builtin: true,
          }),
        });
        return;
      }
      await route.continue();
    });

    await page.goto("/settings/comfyui");
    await expect(page.getByTestId("settings-page")).toBeVisible();
    await expect(page.getByTestId("workflow-list")).toBeVisible();
  });
});

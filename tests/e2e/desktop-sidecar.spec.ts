import { test, expect } from "@playwright/test";

/**
 * M10 desktop sidecar — CI stub.
 *
 * Tauri GUI 测试需图形环境与 WebDriver；本批以手动验证为主。
 * 见 docs/superpowers/plans/2026-06-29-m10-tauri-desktop.md
 */
test.describe("desktop sidecar (stub)", () => {
  test.skip(true, "Tauri desktop E2E deferred to Batch 2 — manual verification required");

  test("sidecar health endpoint returns 200 after desktop launch", async ({ request }) => {
    const response = await request.get("http://127.0.0.1:3000/api/app-info");
    expect(response.ok()).toBeTruthy();
  });
});

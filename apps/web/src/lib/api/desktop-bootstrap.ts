import { getApiBase, getServerOrigin } from "./base";

function isTauriRuntime(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

/** Tauri 桌面启动时从 Rust 拉取 sidecar 端口并注入全局 API base */
export async function bootstrapDesktopApi(): Promise<void> {
  if (typeof window === "undefined") return;
  if (window.__INFINITE_CANVAS_API__) return;
  if (!isTauriRuntime()) return;

  const { invoke } = await import("@tauri-apps/api/core");
  const [apiBase, origin] = await Promise.all([
    invoke<string>("get_api_base"),
    invoke<string>("get_server_origin"),
  ]);

  window.__INFINITE_CANVAS_API__ = apiBase;
  window.__INFINITE_CANVAS_ORIGIN__ = origin;
}

export { getApiBase, getServerOrigin };

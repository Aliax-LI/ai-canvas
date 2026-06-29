declare global {
  interface Window {
    __INFINITE_CANVAS_API__?: string;
    __INFINITE_CANVAS_ORIGIN__?: string;
    __TAURI_INTERNALS__?: unknown;
  }
}

export function getApiBase(): string {
  if (typeof window !== "undefined" && window.__INFINITE_CANVAS_API__) {
    return window.__INFINITE_CANVAS_API__.replace(/\/$/, "");
  }
  return (import.meta.env.VITE_API_BASE ?? "/api").replace(/\/$/, "");
}

export function getServerOrigin(): string {
  if (typeof window !== "undefined" && window.__INFINITE_CANVAS_ORIGIN__) {
    return window.__INFINITE_CANVAS_ORIGIN__.replace(/\/$/, "");
  }

  const apiBase = getApiBase();
  if (apiBase.startsWith("http")) {
    return apiBase.replace(/\/api$/, "");
  }

  return "";
}

/** 桌面端 sidecar 上的非 /api 路径（/generate、/static 等） */
export function resolveServerUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  const origin = getServerOrigin();
  return origin ? `${origin}${normalized}` : normalized;
}

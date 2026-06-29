import { api } from "@/lib/api/client";
import { getApiBase } from "@/lib/api/base";
import type { SmartCanvasData, SmartCanvasSavePayload, SmartMediaItem, SmartNode } from "./types";

export function newSmartClientId(): string {
  return crypto.randomUUID();
}

export function newNodeId(prefix: string): string {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

export async function fetchSmartCanvas(canvasId: string): Promise<SmartCanvasData> {
  const data = await api.get<{ canvas: SmartCanvasData }>(`/canvases/${encodeURIComponent(canvasId)}`);
  const canvas = data.canvas;
  return {
    ...canvas,
    nodes: Array.isArray(canvas.nodes) ? canvas.nodes : [],
    connections: Array.isArray(canvas.connections) ? canvas.connections : [],
    viewport: {
      x: Number(canvas.viewport?.x) || 0,
      y: Number(canvas.viewport?.y) || 0,
      scale: Number(canvas.viewport?.scale) || 1,
    },
    logs: Array.isArray(canvas.logs) ? canvas.logs : [],
    settings: canvas.settings ?? {},
  };
}

export async function saveSmartCanvas(
  canvasId: string,
  payload: SmartCanvasSavePayload,
): Promise<SmartCanvasData> {
  const data = await api.put<{ canvas: SmartCanvasData }>(
    `/canvases/${encodeURIComponent(canvasId)}`,
    payload,
  );
  return data.canvas;
}

export async function uploadSmartMedia(files: File[]): Promise<SmartMediaItem[]> {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  const response = await fetch(`${getApiBase()}/ai/upload`, { method: "POST", body: form });
  const data = (await response.json()) as { files?: { url: string; name: string }[] };
  if (!response.ok) throw new Error("上传失败");
  return (data.files ?? []).map((f) => ({ url: f.url, name: f.name, kind: "image" }));
}

export function mediaPreviewUrl(url: string, width = 320): string {
  if (!url) return "";
  if (url.startsWith("blob:") || url.startsWith("data:")) return url;
  return `/api/media-preview?w=${width}&url=${encodeURIComponent(url)}`;
}

export async function exportSmartGroup(input: {
  group_name: string;
  folder?: string;
  items: { kind: string; url?: string; name?: string; text?: string }[];
}): Promise<{ ok: boolean; folder: string; count: number }> {
  return api.post("/smart-canvas/group-export", input);
}

export function createSmartNode(
  type: SmartNode["type"],
  x: number,
  y: number,
  extra?: Partial<SmartNode>,
): SmartNode {
  const base = { id: newNodeId(type.replace("smart-", "")), type, x, y, created_at: Date.now() };
  switch (type) {
    case "smart-image":
      return {
        ...base,
        title: extra?.images?.length ? "Image" : "上传",
        images: extra?.images ?? [],
        ...extra,
      };
    case "smart-prompt":
      return {
        ...base,
        w: 316,
        h: 240,
        title: "Prompt",
        text: "",
        ...extra,
      };
    case "smart-group":
      return {
        ...base,
        w: 420,
        h: 280,
        title: "智能分组",
        items: [],
        ...extra,
      };
    case "smart-loop":
      return {
        ...base,
        w: 340,
        h: 168,
        title: "Loop",
        count: 1,
        mode: "serial",
        ...extra,
      };
    default:
      return { ...base, ...extra };
  }
}

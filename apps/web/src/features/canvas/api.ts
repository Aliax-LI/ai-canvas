import {
  CANVAS_NODE_REGISTRY,
  type Batch1NodeType,
} from "@infinite-canvas/canvas-schema";
import { api } from "@/lib/api/client";
import { newNodeId } from "./lib/serialize";
import type {
  CanvasEditorData,
  CanvasRecord,
  CanvasSavePayload,
  LegacyCanvasNode,
  ProjectRecord,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE ?? "/api").replace(/\/$/, "");

export function newCanvasClientId(): string {
  return crypto.randomUUID();
}

export async function fetchProjects(): Promise<ProjectRecord[]> {
  const data = await api.get<{ projects: ProjectRecord[] }>("/projects");
  return data.projects;
}

export async function fetchCanvases(): Promise<CanvasRecord[]> {
  const data = await api.get<{ canvases: CanvasRecord[] }>("/canvases");
  return data.canvases;
}

export async function fetchTrashCanvases(): Promise<CanvasRecord[]> {
  const data = await api.get<{ canvases: CanvasRecord[]; retention_days: number }>("/canvases/trash");
  return data.canvases;
}

export async function createProject(name: string): Promise<ProjectRecord> {
  const data = await api.post<{ project: ProjectRecord }>("/projects", { name });
  return data.project;
}

export async function deleteProject(projectId: string): Promise<void> {
  await api.delete(`/projects/${encodeURIComponent(projectId)}`);
}

export async function createCanvas(input: {
  title?: string;
  icon?: string;
  kind?: string;
  project?: string;
  board_x?: number;
  board_y?: number;
}): Promise<CanvasRecord> {
  const data = await api.post<{ canvas: CanvasRecord }>("/canvases", input);
  return data.canvas;
}

export async function updateCanvasMeta(
  canvasId: string,
  patch: Partial<Pick<CanvasRecord, "title" | "icon" | "project" | "board_x" | "board_y" | "pinned">>,
): Promise<CanvasRecord> {
  const data = await api.post<{ canvas: CanvasRecord }>(
    `/canvases/${encodeURIComponent(canvasId)}/meta`,
    patch,
  );
  return data.canvas;
}

export async function deleteCanvas(canvasId: string): Promise<void> {
  await api.delete(`/canvases/${encodeURIComponent(canvasId)}`);
}

export async function restoreCanvas(canvasId: string): Promise<CanvasRecord> {
  const data = await api.post<{ canvas: CanvasRecord }>(
    `/canvases/${encodeURIComponent(canvasId)}/restore`,
    {},
  );
  return data.canvas;
}

export async function purgeCanvas(canvasId: string): Promise<void> {
  await api.delete(`/canvases/${encodeURIComponent(canvasId)}/purge`);
}

export async function fetchCanvasEditor(canvasId: string): Promise<CanvasEditorData> {
  const data = await api.get<{ canvas: CanvasEditorData }>(
    `/canvases/${encodeURIComponent(canvasId)}`,
  );
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

export async function saveCanvasEditor(
  canvasId: string,
  payload: CanvasSavePayload,
): Promise<CanvasEditorData> {
  const data = await api.put<{ canvas: CanvasEditorData }>(
    `/canvases/${encodeURIComponent(canvasId)}`,
    payload,
  );
  return data.canvas;
}

export function createCanvasNode(
  type: Batch1NodeType,
  x: number,
  y: number,
): LegacyCanvasNode {
  const def = CANVAS_NODE_REGISTRY[type];
  const prefix = type === "generator" ? "gen" : type.slice(0, 3);
  const base: LegacyCanvasNode = {
    id: newNodeId(prefix),
    type,
    x,
    y,
    ...def.defaultData,
  };
  if (def.defaultSize) {
    base.w = def.defaultSize.width;
    base.h = def.defaultSize.height;
  }
  return base;
}

export async function uploadCanvasMedia(files: File[]): Promise<{ url: string; name: string }[]> {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  const response = await fetch(`${API_BASE}/ai/upload`, { method: "POST", body: form });
  const data = (await response.json()) as { files?: { url: string; name: string }[] };
  if (!response.ok) throw new Error("上传失败");
  return data.files ?? [];
}

export function mediaPreviewUrl(url: string, width = 320): string {
  if (!url) return "";
  if (url.startsWith("blob:") || url.startsWith("data:")) return url;
  return `/api/media-preview?w=${width}&url=${encodeURIComponent(url)}`;
}

export interface CanvasImageTaskPayload {
  prompt: string;
  provider_id: string;
  model: string;
  size?: string;
  reference_images?: { url: string; name?: string }[];
  quality?: string;
}

export async function createCanvasImageTask(
  payload: CanvasImageTaskPayload,
): Promise<{ task_id: string }> {
  return api.post("/canvas-image-tasks", payload);
}

export async function pollCanvasImageTask(
  taskId: string,
): Promise<{ status: string; result?: { images?: string[] }; error?: string }> {
  return api.get(`/canvas-image-tasks/${encodeURIComponent(taskId)}`);
}

import {
  CANVAS_NODE_REGISTRY,
  type RegisteredNodeType,
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

import { getApiBase } from "@/lib/api/base";

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

const NODE_ID_PREFIX: Partial<Record<RegisteredNodeType, string>> = {
  generator: "gen",
  msgen: "msgen",
  comfy: "comfy",
  ltxDirector: "ltxdir",
  promptGroup: "pg",
  video: "vid",
};

export function createCanvasNode(
  type: RegisteredNodeType,
  x: number,
  y: number,
): LegacyCanvasNode {
  const def = CANVAS_NODE_REGISTRY[type];
  const prefix = NODE_ID_PREFIX[type] ?? type.slice(0, 3);
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
  const response = await fetch(`${getApiBase()}/ai/upload`, { method: "POST", body: form });
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

export interface MsGeneratePayload {
  prompt: string;
  model?: string;
  width?: number;
  height?: number;
  size?: string;
  image_urls?: string[];
  resolution?: string;
  client_id?: string;
}

export async function msGenerate(
  payload: MsGeneratePayload,
): Promise<{ url?: string; task_id?: string }> {
  return api.post("/ms/generate", payload);
}

export interface CanvasVideoPayload {
  prompt: string;
  provider_id?: string;
  model?: string;
  duration?: number;
  aspect_ratio?: string;
  resolution?: string;
  enhance_prompt?: boolean;
  enable_upsample?: boolean;
  watermark?: boolean;
  camerafixed?: boolean;
  generate_audio?: boolean;
  multimodal?: boolean;
}

export async function createCanvasVideo(
  payload: CanvasVideoPayload,
): Promise<{ url?: string; urls?: string[]; video?: string }> {
  return api.post("/canvas-video", payload);
}

export interface CanvasLlmPayload {
  message: string;
  system_prompt?: string;
  model?: string;
  provider?: string;
  ms_model?: string;
  messages?: Record<string, unknown>[];
  images?: string[];
  videos?: string[];
}

export async function createCanvasLlm(
  payload: CanvasLlmPayload,
): Promise<{ text?: string }> {
  return api.post("/canvas-llm", payload);
}

export interface ComfyGeneratePayload {
  prompt?: string;
  width?: number;
  height?: number;
  workflow_json?: string;
  type?: string;
  params?: Record<string, unknown>;
  client_id?: string;
}

export async function createCanvasComfyTask(
  payload: ComfyGeneratePayload,
): Promise<{ task_id: string }> {
  return api.post("/canvas-comfy-tasks", payload);
}

export async function pollCanvasComfyTask(
  taskId: string,
): Promise<{ status: string; result?: { images?: string[] }; error?: string }> {
  return api.get(`/canvas-comfy-tasks/${encodeURIComponent(taskId)}`);
}

export interface RunningHubSubmitPayload {
  webappId?: string;
  nodeInfoList?: Record<string, unknown>[];
  instanceType?: string;
  useWallet?: boolean;
}

export async function submitRunningHub(
  payload: RunningHubSubmitPayload,
): Promise<{ taskId?: string }> {
  return api.post("/runninghub/submit", payload);
}

export interface RunningHubWorkflowSubmitPayload {
  workflowId?: string;
  nodeInfoList?: Record<string, unknown>[];
  useWallet?: boolean;
}

export async function submitRunningHubWorkflow(
  payload: RunningHubWorkflowSubmitPayload,
): Promise<{ taskId?: string }> {
  return api.post("/runninghub/workflow-submit", payload);
}

export async function pollRunningHubTask(
  taskId: string,
): Promise<{ success?: boolean; data?: { status?: string; urls?: string[] } }> {
  return api.get(`/runninghub/query?taskId=${encodeURIComponent(taskId)}`);
}

export interface RunningHubAppEntry {
  id?: string;
  appId?: string;
  workflowId?: string;
  title?: string;
  name?: string;
  enabled?: boolean;
  hidden?: boolean;
}

export interface ApiProviderRecord {
  id: string;
  name?: string;
  rh_apps?: RunningHubAppEntry[];
  rh_workflows?: RunningHubAppEntry[];
}

export async function fetchApiProviders(): Promise<ApiProviderRecord[]> {
  const data = await api.get<{ providers: ApiProviderRecord[] }>("/providers");
  return data.providers ?? [];
}

export async function fetchRunningHubAppInfo(
  webappId: string,
): Promise<{ data?: { nodeInfoList?: unknown[] } }> {
  return api.get(`/runninghub/app-info?webappId=${encodeURIComponent(webappId)}`);
}

export async function uploadUrlToComfy(url: string): Promise<string> {
  const response = await fetch(url);
  if (!response.ok) throw new Error("图片读取失败");
  const blob = await response.blob();
  const filename = url.split("/").pop()?.split("?")[0] || `canvas_${Date.now()}.png`;
  const form = new FormData();
  form.append("files", blob, filename);
  const res = await fetch(`${getApiBase()}/upload`, { method: "POST", body: form });
  const data = (await res.json()) as { files?: { comfy_name?: string; name?: string }[] };
  if (!res.ok) throw new Error("图片上传到 ComfyUI 失败");
  return data.files?.[0]?.comfy_name || filename;
}

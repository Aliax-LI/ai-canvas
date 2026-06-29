import { api } from "@/lib/api/client";
import type { CanvasRecord, ProjectRecord } from "./types";

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

import { api } from "@/lib/api/client";
import type { GenerateResult, HistoryItem } from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE ?? "/api").replace(/\/$/, "");

export function newClientId(): string {
  return crypto.randomUUID();
}

export async function fetchHistory(type: string): Promise<HistoryItem[]> {
  return api.get<HistoryItem[]>(`/history?type=${encodeURIComponent(type)}`);
}

export async function deleteHistory(timestamp: number): Promise<void> {
  await api.post("/history/delete", { timestamp });
}

export async function fetchModelScopeToken(): Promise<string> {
  const data = await api.get<{ token: string }>("/config/token");
  return data.token ?? "";
}

export async function uploadComfyImages(files: File[]): Promise<string[]> {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  const response = await fetch(`${API_BASE}/upload`, { method: "POST", body: form });
  const data = (await response.json()) as { names?: string[]; files?: { name: string }[] };
  if (!response.ok) throw new Error("上传失败");
  if (Array.isArray(data.names)) return data.names;
  if (Array.isArray(data.files)) return data.files.map((f) => f.name);
  return [];
}

export async function uploadAiReferences(files: File[]): Promise<{ url: string; name: string }[]> {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  const response = await fetch(`${API_BASE}/ai/upload`, { method: "POST", body: form });
  const data = (await response.json()) as { files?: { url: string; name: string }[] };
  if (!response.ok) throw new Error("参考图上传失败");
  return data.files ?? [];
}

export async function comfyGenerate(body: Record<string, unknown>): Promise<GenerateResult> {
  return api.post<GenerateResult>("/generate", body);
}

export async function cloudGenerate(body: Record<string, unknown>): Promise<GenerateResult> {
  const response = await fetch("/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const parsed = await response.json();
  if (!response.ok) {
    const detail = (parsed as { detail?: unknown }).detail;
    throw new Error(typeof detail === "string" ? detail : "云端生成失败");
  }
  return parsed as GenerateResult;
}

export async function msGenerate(body: Record<string, unknown>): Promise<GenerateResult> {
  return api.post<GenerateResult>("/ms/generate", body);
}

export async function onlineGenerate(body: Record<string, unknown>): Promise<GenerateResult> {
  return api.post<GenerateResult>("/online-image", body);
}

export async function angleGenerate(body: Record<string, unknown>): Promise<GenerateResult> {
  return api.post<GenerateResult>("/angle/generate", body);
}

export async function anglePoll(body: Record<string, unknown>): Promise<GenerateResult> {
  return api.post<GenerateResult>("/angle/poll_status", body);
}

export function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export function alignMsSize(w: number, h: number): { width: number; height: number } {
  if (!w || !h) return { width: 1024, height: 1024 };
  const MIN = 512;
  const MAX = 2048;
  let width = Math.round(w);
  let height = Math.round(h);
  const longest = Math.max(width, height);
  if (longest > MAX) {
    const scale = MAX / longest;
    width = Math.round(width * scale);
    height = Math.round(height * scale);
  }
  const align = (v: number) => Math.min(MAX, Math.max(MIN, Math.round(v / 64) * 64));
  return { width: align(width), height: align(height) };
}

import type { OutputNodeData } from "@infinite-canvas/canvas-schema";
import { outputUrlValue } from "./graph";

export interface CanvasLogEntry {
  id: string;
  ts: number;
  nodeId: string;
  nodeType?: string;
  status: "running" | "succeeded" | "failed";
  message?: string;
}

export function newLogEntry(
  partial: Omit<CanvasLogEntry, "id" | "ts"> & { ts?: number },
): CanvasLogEntry {
  return {
    id: `log_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`,
    ts: partial.ts ?? Date.now(),
    nodeId: partial.nodeId,
    nodeType: partial.nodeType,
    status: partial.status,
    message: partial.message,
  };
}

export function mergeGeneratedOutputs(
  existing: unknown[] | undefined,
  urls: string[],
  kind = "image",
): unknown[] {
  const prev = Array.isArray(existing) ? existing : [];
  const items = urls.map((url) => ({ url, kind }));
  return [...prev, ...items];
}

export function mergeOutputImages(
  existing: OutputNodeData["images"] | undefined,
  urls: string[],
): OutputNodeData["images"] {
  const prev = Array.isArray(existing) ? [...existing] : [];
  for (const url of urls) {
    if (!url) continue;
    const dup = prev.some((item) => outputUrlValue(item) === url);
    if (!dup) prev.push({ url, name: "generated.png", kind: "image" });
  }
  return prev;
}

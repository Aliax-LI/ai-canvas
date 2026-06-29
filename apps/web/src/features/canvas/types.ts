import type { RegisteredNodeType } from "@infinite-canvas/canvas-schema";

export interface CanvasRecord {
  id: string;
  title: string;
  icon: string;
  kind: string;
  project: string;
  board_x?: number | null;
  board_y?: number | null;
  pinned?: boolean;
  color?: string;
  created_at: number;
  updated_at: number;
  node_count?: number;
  deleted_at?: number;
}

export interface ProjectRecord {
  id: string;
  name: string;
  order?: number;
}

/** 与上游 `data/canvases/*.json` 兼容的节点结构 */
export interface LegacyCanvasNode {
  id: string;
  type: string;
  x: number;
  y: number;
  w?: number;
  h?: number;
  [key: string]: unknown;
}

export interface LegacyConnection {
  id: string;
  from: string;
  to: string;
}

export interface CanvasViewport {
  x: number;
  y: number;
  scale: number;
}

export interface CanvasEditorData {
  id: string;
  title: string;
  icon: string;
  kind: string;
  nodes: LegacyCanvasNode[];
  connections: LegacyConnection[];
  viewport: CanvasViewport;
  logs: Record<string, unknown>[];
  settings: Record<string, unknown>;
  updated_at: number;
}

export interface CanvasSavePayload {
  title: string;
  icon: string;
  nodes: LegacyCanvasNode[];
  connections: LegacyConnection[];
  viewport: CanvasViewport;
  logs: Record<string, unknown>[];
  settings: Record<string, unknown>;
  base_updated_at: number;
  client_id: string;
}

export type CreateNodeType = RegisteredNodeType;

export type SaveState = "idle" | "pending" | "saving" | "saved" | "error";

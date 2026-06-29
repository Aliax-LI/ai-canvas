export type SmartNodeType = "smart-image" | "smart-prompt" | "smart-group" | "smart-loop";

export interface SmartMediaItem {
  url?: string;
  name?: string;
  kind?: string;
}

export interface SmartNode {
  id: string;
  type: SmartNodeType;
  x: number;
  y: number;
  w?: number;
  h?: number;
  title?: string;
  text?: string;
  images?: SmartMediaItem[];
  items?: SmartNode[];
  count?: number;
  mode?: string;
  created_at?: number;
  [key: string]: unknown;
}

export interface SmartViewport {
  x: number;
  y: number;
  scale: number;
}

export interface SmartCanvasData {
  id: string;
  title: string;
  icon: string;
  kind: string;
  nodes: SmartNode[];
  connections: Record<string, unknown>[];
  viewport: SmartViewport;
  logs: Record<string, unknown>[];
  settings: Record<string, unknown>;
  updated_at: number;
}

export interface SmartCanvasSavePayload {
  title: string;
  icon: string;
  nodes: SmartNode[];
  connections: Record<string, unknown>[];
  viewport: SmartViewport;
  logs: Record<string, unknown>[];
  settings: Record<string, unknown>;
  base_updated_at: number;
  client_id: string;
}

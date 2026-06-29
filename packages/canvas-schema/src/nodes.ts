/** 无限画布节点类型（与上游 `canvas.js` type 字段一一对应） */

export type CanvasNodeType =
  | "image"
  | "prompt"
  | "output"
  | "group"
  | "generator"
  | "msgen"
  | "comfy"
  | "rh"
  | "video"
  | "llm"
  | "loop"
  | "text"
  | "ltxDirector"
  | "promptGroup"
  | string;

export type CanvasNodeCategory =
  | "image"
  | "prompt"
  | "api"
  | "comfyui"
  | "llm"
  | "video"
  | "output"
  | "loop"
  | "other";

export interface CanvasNodeDefinition<TData = Record<string, unknown>> {
  type: CanvasNodeType;
  label: string;
  category: CanvasNodeCategory;
  accentColor: string;
  defaultData: TData;
  defaultSize?: { width: number; height: number };
}

export interface ImageNodeData {
  url: string;
  name: string;
  mediaKind?: string;
}

export interface PromptNodeData {
  text: string;
}

export interface OutputNodeData {
  images: { url?: string; name?: string; kind?: string }[];
}

export interface GroupNodeData {
  w: number;
  h: number;
  items: string[];
}

export interface GeneratorNodeData {
  apiProvider: string;
  model: string;
  ratio: string;
  resolution: string;
  customRatio: string;
  customSize: string;
  customRatioWidth: string;
  customRatioHeight: string;
  customWidth: string;
  customHeight: string;
  inputs: string[];
  count?: number;
  quality?: string;
  running?: boolean;
  runStatus?: string;
  runError?: string;
  generatedOutputs?: unknown[];
}

/** M9 Batch 1 已实现节点 */
export const BATCH1_NODE_TYPES = [
  "image",
  "prompt",
  "output",
  "group",
  "generator",
] as const;

export type Batch1NodeType = (typeof BATCH1_NODE_TYPES)[number];

export const CANVAS_NODE_REGISTRY: Record<Batch1NodeType, CanvasNodeDefinition> = {
  image: {
    type: "image",
    label: "图片",
    category: "image",
    accentColor: "#71717A",
    defaultData: { url: "", name: "空白图片" },
    defaultSize: { width: 220, height: 180 },
  },
  prompt: {
    type: "prompt",
    label: "提示词",
    category: "prompt",
    accentColor: "#52525B",
    defaultData: { text: "" },
    defaultSize: { width: 280, height: 160 },
  },
  output: {
    type: "output",
    label: "输出",
    category: "output",
    accentColor: "#18181B",
    defaultData: { images: [] },
    defaultSize: { width: 240, height: 200 },
  },
  group: {
    type: "group",
    label: "分组",
    category: "other",
    accentColor: "#71717A",
    defaultData: { w: 300, h: 220, items: [] },
    defaultSize: { width: 300, height: 220 },
  },
  generator: {
    type: "generator",
    label: "API 生图",
    category: "api",
    accentColor: "#2563EB",
    defaultData: {
      apiProvider: "comfly",
      model: "",
      ratio: "square",
      resolution: "1k",
      customRatio: "",
      customSize: "",
      customRatioWidth: "",
      customRatioHeight: "",
      customWidth: "",
      customHeight: "",
      inputs: [],
      count: 1,
    },
    defaultSize: { width: 280, height: 220 },
  },
};

/** 待后续批次迁移的节点类型 */
export const PENDING_NODE_TYPES: { type: CanvasNodeType; label: string }[] = [
  { type: "msgen", label: "ModelScope 生图" },
  { type: "comfy", label: "ComfyUI" },
  { type: "rh", label: "RunningHub" },
  { type: "video", label: "视频生成" },
  { type: "llm", label: "LLM" },
  { type: "loop", label: "循环" },
  { type: "text", label: "文本" },
  { type: "ltxDirector", label: "LTX Director" },
  { type: "promptGroup", label: "提示词组" },
];

export function isBatch1NodeType(type: string): type is Batch1NodeType {
  return (BATCH1_NODE_TYPES as readonly string[]).includes(type);
}

export function getNodeDefinition(type: string): CanvasNodeDefinition | undefined {
  if (isBatch1NodeType(type)) return CANVAS_NODE_REGISTRY[type];
  return undefined;
}

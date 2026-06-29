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

export interface MsGenNodeData {
  msgenModel: string;
  msWidth: number;
  msHeight: number;
  msCustomModel: string;
  msRatio: string;
  msResolution: string;
  msCustomRatio: string;
  msCustomSize: string;
  msCustomRatioWidth: string;
  msCustomRatioHeight: string;
  msCustomWidth: string;
  msCustomHeight: string;
  count: number;
  fitImage: boolean;
  inputs: string[];
  running?: boolean;
  runStatus?: string;
  runError?: string;
}

export interface ComfyNodeData {
  mode: string;
  width: number;
  height: number;
  enhanceStrength: number;
  enhanceUpscale: boolean;
  enhanceUpscaleRes: number;
  editUpscale: boolean;
  editUpscaleRes: number;
  editModel: string;
  ratio: string;
  resolution: string;
  customRatio: string;
  customSize: string;
  customRatioWidth: string;
  customRatioHeight: string;
  customWidth: string;
  customHeight: string;
  comfyWorkflow: string;
  comfyParams: Record<string, unknown>;
  count: number;
  inputs: string[];
  running?: boolean;
  runStatus?: string;
  runError?: string;
}

export interface RhNodeData {
  rhMode: string;
  rhPayment: string;
  webappId: string;
  workflowId: string;
  instanceType: string;
  rhAppInfo: unknown;
  rhWorkflowInfo: unknown;
  rhParams: Record<string, unknown>;
  inputs: string[];
  running?: boolean;
  runStatus?: string;
  runError?: string;
}

export interface VideoNodeData {
  apiProvider: string;
  model: string;
  duration: number;
  aspectRatio: string;
  resolution: string;
  enhancePrompt: boolean;
  enableUpsample: boolean;
  watermark: boolean;
  cameraFixed: boolean;
  generateAudio: boolean;
  useFrameRoles: boolean;
  multimodal: boolean;
  tempShLinks: unknown[];
  inputs: string[];
  running?: boolean;
  runStatus?: string;
  runError?: string;
}

export interface LlmNodeData {
  llmProvider: string;
  model: string;
  mode: string;
  systemPrompt: string;
  chatInput: string;
  messages: unknown[];
  outputText: string;
  llmInputHeight: number;
  llmOutputHeight: number;
  running?: boolean;
  runStatus?: string;
  runError?: string;
}

export interface LoopNodeData {
  count: number;
  mode: string;
  showPrompt: boolean;
  imageInput: boolean;
  videoInput: boolean;
  loopStart: number;
  imageBatchSize: number;
  videoBatchSize: number;
  variablePrompt: string;
  fixedPrompt: string;
  running?: boolean;
  runStatus?: string;
  runError?: string;
}

export interface TextNodeData {
  prompt: string;
  start?: number;
  length?: number;
  color?: string;
  strength?: number;
  imageRef?: unknown;
}

export interface LtxDirectorNodeData {
  globalPrompt: string;
  durationFrames: number;
  durationSeconds: number;
  frameRate: number;
  customWidth: number;
  customHeight: number;
  displayMode: string;
  useCustomAudio: boolean;
  imgCompression: number;
  epsilon: number;
  divisibleBy: number;
  noiseSeed: number;
  ltxTimelineData: string;
  ltxLocalPrompts: string;
  ltxSegmentLengths: string;
  ltxGuideStrength: string;
  ltxSegments: unknown[];
  ltxSelectedSegId: string;
  inputs: string[];
  running?: boolean;
  runStatus?: string;
  runError?: string;
}

export interface PromptGroupNodeData {
  items: string[];
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

/** M9 Batch 2 节点 */
export const BATCH2_NODE_TYPES = [
  "msgen",
  "comfy",
  "rh",
  "video",
  "llm",
  "loop",
  "text",
  "ltxDirector",
  "promptGroup",
] as const;

export type Batch2NodeType = (typeof BATCH2_NODE_TYPES)[number];

export type RegisteredNodeType = Batch1NodeType | Batch2NodeType;

export const ALL_REGISTERED_NODE_TYPES = [
  ...BATCH1_NODE_TYPES,
  ...BATCH2_NODE_TYPES,
] as const;

const BATCH1_REGISTRY: Record<Batch1NodeType, CanvasNodeDefinition> = {
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

const BATCH2_REGISTRY: Record<Batch2NodeType, CanvasNodeDefinition> = {
  msgen: {
    type: "msgen",
    label: "ModelScope 生图",
    category: "api",
    accentColor: "#7C3AED",
    defaultData: {
      msgenModel: "zimage",
      msWidth: 1024,
      msHeight: 1024,
      msCustomModel: "Tongyi-MAI/Z-Image-Turbo",
      msRatio: "square",
      msResolution: "1k",
      msCustomRatio: "",
      msCustomSize: "",
      msCustomRatioWidth: "",
      msCustomRatioHeight: "",
      msCustomWidth: "",
      msCustomHeight: "",
      count: 1,
      fitImage: false,
      inputs: [],
      running: false,
    },
    defaultSize: { width: 280, height: 220 },
  },
  comfy: {
    type: "comfy",
    label: "ComfyUI",
    category: "comfyui",
    accentColor: "#EA580C",
    defaultData: {
      mode: "text",
      width: 1024,
      height: 1024,
      enhanceStrength: 0.5,
      enhanceUpscale: false,
      enhanceUpscaleRes: 2048,
      editUpscale: false,
      editUpscaleRes: 2048,
      editModel: "",
      ratio: "square",
      resolution: "1k",
      customRatio: "",
      customSize: "",
      customRatioWidth: "",
      customRatioHeight: "",
      customWidth: "",
      customHeight: "",
      comfyWorkflow: "",
      comfyParams: {},
      count: 1,
      inputs: [],
    },
    defaultSize: { width: 420, height: 460 },
  },
  rh: {
    type: "rh",
    label: "RunningHub",
    category: "comfyui",
    accentColor: "#0891B2",
    defaultData: {
      rhMode: "app",
      rhPayment: "free",
      webappId: "",
      workflowId: "",
      instanceType: "",
      rhAppInfo: null,
      rhWorkflowInfo: null,
      rhParams: {},
      inputs: [],
      running: false,
    },
    defaultSize: { width: 430, height: 200 },
  },
  video: {
    type: "video",
    label: "视频生成",
    category: "video",
    accentColor: "#DB2777",
    defaultData: {
      apiProvider: "comfly",
      model: "veo3-fast",
      duration: 5,
      aspectRatio: "16:9",
      resolution: "",
      enhancePrompt: false,
      enableUpsample: false,
      watermark: false,
      cameraFixed: false,
      generateAudio: false,
      useFrameRoles: false,
      multimodal: false,
      tempShLinks: [],
      inputs: [],
      running: false,
    },
    defaultSize: { width: 280, height: 240 },
  },
  llm: {
    type: "llm",
    label: "LLM",
    category: "llm",
    accentColor: "#059669",
    defaultData: {
      llmProvider: "comfly",
      model: "",
      mode: "node",
      systemPrompt:
        "You are a helpful assistant. Rewrite the input into a concise image prompt.",
      chatInput: "",
      messages: [],
      outputText: "",
      llmInputHeight: 110,
      llmOutputHeight: 150,
      running: false,
    },
    defaultSize: { width: 300, height: 280 },
  },
  loop: {
    type: "loop",
    label: "循环",
    category: "loop",
    accentColor: "#CA8A04",
    defaultData: {
      count: 3,
      mode: "serial",
      showPrompt: false,
      imageInput: false,
      videoInput: false,
      loopStart: 1,
      imageBatchSize: 1,
      videoBatchSize: 1,
      variablePrompt: "",
      fixedPrompt: "",
    },
    defaultSize: { width: 260, height: 200 },
  },
  text: {
    type: "text",
    label: "文本段",
    category: "prompt",
    accentColor: "#52525B",
    defaultData: {
      prompt: "",
      start: 0,
      length: 120,
      strength: 1,
    },
    defaultSize: { width: 240, height: 120 },
  },
  ltxDirector: {
    type: "ltxDirector",
    label: "LTX Director",
    category: "video",
    accentColor: "#9333EA",
    defaultData: {
      globalPrompt: "",
      durationFrames: 120,
      durationSeconds: 5,
      frameRate: 24,
      customWidth: 0,
      customHeight: 0,
      displayMode: "seconds",
      useCustomAudio: false,
      imgCompression: 18,
      epsilon: 0.001,
      divisibleBy: 32,
      noiseSeed: 12,
      ltxTimelineData: "",
      ltxLocalPrompts: "",
      ltxSegmentLengths: "",
      ltxGuideStrength: "",
      ltxSegments: [],
      ltxSelectedSegId: "",
      inputs: [],
      running: false,
    },
    defaultSize: { width: 1000, height: 800 },
  },
  promptGroup: {
    type: "promptGroup",
    label: "提示词组",
    category: "prompt",
    accentColor: "#52525B",
    defaultData: { items: [] },
    defaultSize: { width: 320, height: 200 },
  },
};

/** 全部已注册节点（Batch 1 + Batch 2） */
export const CANVAS_NODE_REGISTRY: Record<RegisteredNodeType, CanvasNodeDefinition> = {
  ...BATCH1_REGISTRY,
  ...BATCH2_REGISTRY,
};

export function isBatch1NodeType(type: string): type is Batch1NodeType {
  return (BATCH1_NODE_TYPES as readonly string[]).includes(type);
}

export function isBatch2NodeType(type: string): type is Batch2NodeType {
  return (BATCH2_NODE_TYPES as readonly string[]).includes(type);
}

export function isRegisteredNodeType(type: string): type is RegisteredNodeType {
  return (ALL_REGISTERED_NODE_TYPES as readonly string[]).includes(type);
}

export function getNodeDefinition(type: string): CanvasNodeDefinition | undefined {
  if (isRegisteredNodeType(type)) return CANVAS_NODE_REGISTRY[type];
  return undefined;
}

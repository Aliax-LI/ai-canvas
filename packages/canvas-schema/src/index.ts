/** 画布节点类型标识（与上游 node type 一一对应，M4 仅占位） */
export type CanvasNodeType = string;

export interface CanvasNodeDefinition<TData = Record<string, unknown>> {
  type: CanvasNodeType;
  label: string;
  category: "image" | "prompt" | "api" | "comfyui" | "llm" | "video" | "output" | "loop" | "other";
  defaultData: TData;
}

/** 节点注册表类型 stub；M5+ 按节点类型分批填充 */
export type CanvasNodeRegistry = Record<CanvasNodeType, CanvasNodeDefinition>;

export const EMPTY_NODE_REGISTRY: CanvasNodeRegistry = {};

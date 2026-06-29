import type { NodeTypes } from "@xyflow/react";
import { ComfyNode } from "./nodes/ComfyNode";
import { FallbackNode } from "./nodes/FallbackNode";
import { GeneratorNode } from "./nodes/GeneratorNode";
import { GroupNode } from "./nodes/GroupNode";
import { ImageNode } from "./nodes/ImageNode";
import { LlmNode } from "./nodes/LlmNode";
import { LoopNode } from "./nodes/LoopNode";
import { LtxDirectorNode } from "./nodes/LtxDirectorNode";
import { MsGenNode } from "./nodes/MsGenNode";
import { OutputNode } from "./nodes/OutputNode";
import { PromptGroupNode } from "./nodes/PromptGroupNode";
import { PromptNode } from "./nodes/PromptNode";
import { RhNode } from "./nodes/RhNode";
import { TextNode } from "./nodes/TextNode";
import { VideoNode } from "./nodes/VideoNode";

export const canvasNodeTypes: NodeTypes = {
  image: ImageNode,
  prompt: PromptNode,
  output: OutputNode,
  group: GroupNode,
  generator: GeneratorNode,
  msgen: MsGenNode,
  comfy: ComfyNode,
  rh: RhNode,
  video: VideoNode,
  llm: LlmNode,
  loop: LoopNode,
  text: TextNode,
  ltxDirector: LtxDirectorNode,
  promptGroup: PromptGroupNode,
  fallback: FallbackNode,
};

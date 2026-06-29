import type { NodeTypes } from "@xyflow/react";
import { GeneratorNode } from "./nodes/GeneratorNode";
import { GroupNode } from "./nodes/GroupNode";
import { ImageNode } from "./nodes/ImageNode";
import { OutputNode } from "./nodes/OutputNode";
import { PromptNode } from "./nodes/PromptNode";

export const canvasNodeTypes: NodeTypes = {
  image: ImageNode,
  prompt: PromptNode,
  output: OutputNode,
  group: GroupNode,
  generator: GeneratorNode,
};

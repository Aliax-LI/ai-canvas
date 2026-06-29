import { Textarea } from "@/components/ui/textarea";
import { useCanvasEditorActions } from "../EditorActionsContext";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { PromptNodeData } from "@infinite-canvas/canvas-schema";

export function PromptNode({ id, data, selected }: CanvasNodeProps<PromptNodeData>) {
  const text = String(data.text ?? "");
  const { updateNodeData } = useCanvasEditorActions();

  return (
    <BaseNodeShell
      type="prompt"
      title="提示词"
      selected={selected}
      data-testid={`canvas-node-${id}`}
    >
      <Textarea
        value={text}
        onChange={(e) => updateNodeData(id, { text: e.target.value })}
        placeholder="输入提示词…"
        className="nodrag min-h-[80px] resize-none border-none bg-muted/50 p-2 text-xs shadow-none focus-visible:ring-0"
        data-testid={`canvas-prompt-text-${id}`}
      />
    </BaseNodeShell>
  );
}

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { TextNodeData } from "@infinite-canvas/canvas-schema";

export function TextNode({ id, data, selected }: CanvasNodeProps<TextNodeData>) {
  const prompt = String(data.prompt ?? "");
  const length = Number(data.length ?? 120);

  return (
    <BaseNodeShell
      type="text"
      title="文本段"
      selected={selected}
      data-testid={`canvas-node-${id}`}
    >
      <div className="space-y-2 nodrag">
        <div>
          <Label className="text-xs text-muted-foreground">提示词</Label>
          <Input value={prompt} readOnly placeholder="空文本段" className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs text-muted-foreground">长度</Label>
          <Input value={`${length} 帧`} readOnly className="h-7 text-xs" />
        </div>
      </div>
    </BaseNodeShell>
  );
}

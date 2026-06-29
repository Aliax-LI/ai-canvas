import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { stubBatch3Run } from "../../lib/nodeRun";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { PromptGroupNodeData } from "@infinite-canvas/canvas-schema";
import { Button } from "@/components/ui/button";
import { Play } from "lucide-react";

export function PromptGroupNode({ id, data, selected }: CanvasNodeProps<PromptGroupNodeData>) {
  const items = Array.isArray(data.items) ? data.items : [];

  return (
    <BaseNodeShell
      type="promptGroup"
      title="提示词组"
      selected={selected}
      data-testid={`canvas-node-${id}`}
    >
      <div className="space-y-2 nodrag">
        <div>
          <Label className="text-xs text-muted-foreground">成员数</Label>
          <Input value={String(items.length)} readOnly className="h-7 text-xs" />
        </div>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="w-full"
          data-testid={`canvas-promptgroup-run-${id}`}
          onClick={() => stubBatch3Run("提示词组")}
        >
          <Play className="mr-1 size-3" />
          运行
        </Button>
      </div>
    </BaseNodeShell>
  );
}

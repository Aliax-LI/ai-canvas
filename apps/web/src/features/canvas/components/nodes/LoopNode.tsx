import { useCallback, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { stubBatch3Run } from "../../lib/nodeRun";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { LoopNodeData } from "@infinite-canvas/canvas-schema";

export function LoopNode({ id, data, selected }: CanvasNodeProps<LoopNodeData>) {
  const [running, setRunning] = useState(Boolean(data.running));
  const count = Number(data.count ?? 3);
  const mode = String(data.mode ?? "serial");

  const handleRun = useCallback(() => {
    setRunning(true);
    stubBatch3Run("循环节点");
    setTimeout(() => setRunning(false), 800);
  }, []);

  return (
    <BaseNodeShell
      type="loop"
      title="循环"
      selected={selected}
      running={running}
      data-testid={`canvas-node-${id}`}
    >
      <div className="space-y-2 nodrag">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <Label className="text-xs text-muted-foreground">次数</Label>
            <Input value={String(count)} readOnly className="h-7 text-xs" />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">模式</Label>
            <Input value={mode} readOnly className="h-7 text-xs" />
          </div>
        </div>
        <Button
          type="button"
          size="sm"
          className="w-full"
          disabled={running}
          data-testid={`canvas-loop-run-${id}`}
          onClick={handleRun}
        >
          {running ? <Loader2 className="mr-1 size-3 animate-spin" /> : <Play className="mr-1 size-3" />}
          运行
        </Button>
      </div>
    </BaseNodeShell>
  );
}

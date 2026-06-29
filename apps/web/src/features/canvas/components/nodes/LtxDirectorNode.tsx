import { useCallback, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { LtxDirectorNodeData } from "@infinite-canvas/canvas-schema";

export function LtxDirectorNode({ id, data, selected }: CanvasNodeProps<LtxDirectorNodeData>) {
  const [running, setRunning] = useState(Boolean(data.running));
  const durationSeconds = Number(data.durationSeconds ?? 5);
  const frameRate = Number(data.frameRate ?? 24);
  const segmentCount = Array.isArray(data.ltxSegments) ? data.ltxSegments.length : 0;

  const handleRun = useCallback(() => {
    setRunning(true);
    toast.info("LTX Director 完整运行将在 Batch 4 实现");
    setTimeout(() => setRunning(false), 800);
  }, []);

  return (
    <BaseNodeShell
      type="ltxDirector"
      title="LTX Director"
      selected={selected}
      running={running}
      className="min-w-[280px]"
      data-testid={`canvas-node-${id}`}
    >
      <div className="space-y-2 nodrag">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <Label className="text-xs text-muted-foreground">时长</Label>
            <Input value={`${durationSeconds}s`} readOnly className="h-7 text-xs" />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">帧率</Label>
            <Input value={`${frameRate} fps`} readOnly className="h-7 text-xs" />
          </div>
        </div>
        <div>
          <Label className="text-xs text-muted-foreground">片段数</Label>
          <Input value={String(segmentCount)} readOnly className="h-7 text-xs" />
        </div>
        <Button
          type="button"
          size="sm"
          className="w-full"
          disabled={running}
          data-testid={`canvas-ltx-run-${id}`}
          onClick={handleRun}
        >
          {running ? <Loader2 className="mr-1 size-3 animate-spin" /> : <Play className="mr-1 size-3" />}
          运行
        </Button>
      </div>
    </BaseNodeShell>
  );
}

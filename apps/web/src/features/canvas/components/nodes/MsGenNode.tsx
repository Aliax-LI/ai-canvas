import { useCallback, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { msGenerate, newCanvasClientId } from "../../api";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { MsGenNodeData } from "@infinite-canvas/canvas-schema";

export function MsGenNode({ id, data, selected }: CanvasNodeProps<MsGenNodeData>) {
  const [running, setRunning] = useState(Boolean(data.running));
  const modelKey = String(data.msgenModel ?? "zimage");
  const customModel = String(data.msCustomModel ?? "");
  const width = Number(data.msWidth ?? 1024);
  const height = Number(data.msHeight ?? 1024);
  const runError = String(data.runError ?? "");

  const handleRun = useCallback(async () => {
    setRunning(true);
    try {
      const payload =
        modelKey === "zimage"
          ? {
              prompt: "A beautiful landscape",
              resolution: `${width}x${height}`,
              client_id: newCanvasClientId(),
            }
          : {
              prompt: "A beautiful landscape",
              model: customModel || "Tongyi-MAI/Z-Image-Turbo",
              width,
              height,
              size: `${width}x${height}`,
              client_id: newCanvasClientId(),
            };
      const result = await msGenerate(payload);
      if (result.url) toast.success("ModelScope 生成完成");
      else toast.success("ModelScope 任务已提交");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "ModelScope 生成失败");
    } finally {
      setRunning(false);
    }
  }, [modelKey, customModel, width, height]);

  return (
    <BaseNodeShell
      type="msgen"
      title="ModelScope 生图"
      selected={selected}
      running={running}
      data-testid={`canvas-node-${id}`}
    >
      <div className="space-y-2 nodrag">
        <div>
          <Label className="text-xs text-muted-foreground">模型类型</Label>
          <Input value={modelKey} readOnly className="h-7 text-xs" />
        </div>
        {modelKey === "custom" ? (
          <div>
            <Label className="text-xs text-muted-foreground">自定义模型</Label>
            <Input value={customModel} readOnly className="h-7 text-xs" />
          </div>
        ) : null}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <Label className="text-xs text-muted-foreground">宽</Label>
            <Input value={String(width)} readOnly className="h-7 text-xs" />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">高</Label>
            <Input value={String(height)} readOnly className="h-7 text-xs" />
          </div>
        </div>
        {runError ? <p className="text-xs text-destructive">{runError}</p> : null}
        <Button
          type="button"
          size="sm"
          className="w-full"
          disabled={running}
          data-testid={`canvas-msgen-run-${id}`}
          onClick={() => void handleRun()}
        >
          {running ? <Loader2 className="mr-1 size-3 animate-spin" /> : <Play className="mr-1 size-3" />}
          运行
        </Button>
      </div>
    </BaseNodeShell>
  );
}

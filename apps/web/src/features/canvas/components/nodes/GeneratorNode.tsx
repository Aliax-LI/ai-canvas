import { useCallback, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createCanvasImageTask, pollCanvasImageTask } from "../../api";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { GeneratorNodeData } from "@infinite-canvas/canvas-schema";

async function waitForTask(taskId: string): Promise<string[]> {
  for (let i = 0; i < 60; i++) {
    const result = await pollCanvasImageTask(taskId);
    if (result.status === "succeeded") return result.result?.images ?? [];
    if (result.status === "failed") throw new Error(result.error ?? "生成失败");
    await new Promise((r) => setTimeout(r, 1600));
  }
  throw new Error("生成超时");
}

export function GeneratorNode({ id, data, selected }: CanvasNodeProps<GeneratorNodeData>) {
  const [running, setRunning] = useState(Boolean(data.running));
  const provider = String(data.apiProvider ?? "comfly");
  const model = String(data.model ?? "");
  const ratio = String(data.ratio ?? "square");
  const resolution = String(data.resolution ?? "1k");
  const runStatus = String(data.runStatus ?? "");
  const runError = String(data.runError ?? "");

  const handleRun = useCallback(async () => {
    setRunning(true);
    try {
      const task = await createCanvasImageTask({
        prompt: "A beautiful landscape",
        provider_id: provider,
        model: model || "dall-e-3",
        size: resolution === "1k" ? "1024x1024" : "512x512",
      });
      await waitForTask(task.task_id);
      toast.success("生成任务已提交");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "生成失败");
    } finally {
      setRunning(false);
    }
  }, [provider, model, resolution]);

  return (
    <BaseNodeShell
      type="generator"
      title="API 生图"
      selected={selected}
      running={running}
      error={runStatus === "failed"}
      data-testid={`canvas-node-${id}`}
    >
      <div className="space-y-2 nodrag">
        <div>
          <Label className="text-xs text-muted-foreground">平台</Label>
          <Input value={provider} readOnly className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs text-muted-foreground">模型</Label>
          <Input value={model} readOnly placeholder="默认模型" className="h-7 text-xs" />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <Label className="text-xs text-muted-foreground">比例</Label>
            <Input value={ratio} readOnly className="h-7 text-xs" />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">分辨率</Label>
            <Input value={resolution} readOnly className="h-7 text-xs" />
          </div>
        </div>
        {runError ? <p className="text-xs text-destructive">{runError}</p> : null}
        <Button
          type="button"
          size="sm"
          className="w-full"
          disabled={running}
          data-testid={`canvas-generator-run-${id}`}
          onClick={() => void handleRun()}
        >
          {running ? (
            <Loader2 className="mr-1 size-3 animate-spin" />
          ) : (
            <Play className="mr-1 size-3" />
          )}
          运行
        </Button>
      </div>
    </BaseNodeShell>
  );
}

import { useCallback, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { submitRunningHub, submitRunningHubWorkflow } from "../../api";
import { waitForRhTask } from "../../lib/nodeRun";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { RhNodeData } from "@infinite-canvas/canvas-schema";

export function RhNode({ id, data, selected }: CanvasNodeProps<RhNodeData>) {
  const [running, setRunning] = useState(Boolean(data.running));
  const rhMode = String(data.rhMode ?? "app");
  const webappId = String(data.webappId ?? "");
  const workflowId = String(data.workflowId ?? "");
  const runError = String(data.runError ?? "");

  const handleRun = useCallback(async () => {
    setRunning(true);
    try {
      const submit =
        rhMode === "workflow"
          ? await submitRunningHubWorkflow({ workflowId, nodeInfoList: [] })
          : await submitRunningHub({ webappId, nodeInfoList: [] });
      if (!submit.taskId) throw new Error("未返回 taskId");
      await waitForRhTask(submit.taskId);
      toast.success("RunningHub 任务完成");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "RunningHub 运行失败");
    } finally {
      setRunning(false);
    }
  }, [rhMode, webappId, workflowId]);

  return (
    <BaseNodeShell
      type="rh"
      title="RunningHub"
      selected={selected}
      running={running}
      data-testid={`canvas-node-${id}`}
    >
      <div className="space-y-2 nodrag">
        <div>
          <Label className="text-xs text-muted-foreground">模式</Label>
          <Input value={rhMode} readOnly className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs text-muted-foreground">
            {rhMode === "workflow" ? "工作流 ID" : "应用 ID"}
          </Label>
          <Input
            value={rhMode === "workflow" ? workflowId : webappId}
            readOnly
            placeholder="未配置"
            className="h-7 text-xs"
          />
        </div>
        {runError ? <p className="text-xs text-destructive">{runError}</p> : null}
        <Button
          type="button"
          size="sm"
          className="w-full"
          disabled={running}
          data-testid={`canvas-rh-run-${id}`}
          onClick={() => void handleRun()}
        >
          {running ? <Loader2 className="mr-1 size-3 animate-spin" /> : <Play className="mr-1 size-3" />}
          运行
        </Button>
      </div>
    </BaseNodeShell>
  );
}

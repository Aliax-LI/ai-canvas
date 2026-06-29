import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useCanvasEditorActions } from "../EditorActionsContext";
import { NodeRunActions } from "../NodeRunActions";
import { runRhNode, type RunNodeRuntime } from "../../lib/runNode";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { RhNodeData } from "@infinite-canvas/canvas-schema";

export function RhNode({ id, data, selected }: CanvasNodeProps<RhNodeData>) {
  const { nodes, edges, updateNodeData, appendLog, writeOutputImages } = useCanvasEditorActions();
  const [running, setRunning] = useState(Boolean(data.running));
  const rhMode = String(data.rhMode ?? "app");
  const webappId = String(data.webappId ?? "");
  const workflowId = String(data.workflowId ?? "");
  const runError = String(data.runError ?? "");
  const cascadeIdx = String(data._cascadeIdx ?? "");
  const rhParams = (data.rhParams ?? {}) as Record<string, unknown>;
  const rhParamsJson = useMemo(() => JSON.stringify(rhParams, null, 2), [rhParams]);

  const runtime = useMemo<RunNodeRuntime>(
    () => ({
      nodes,
      edges,
      getNodes: () => nodes,
      getEdges: () => edges,
      updateNodeData,
      appendLog,
      writeOutputImages,
    }),
    [nodes, edges, updateNodeData, appendLog, writeOutputImages],
  );

  const nodeRef = useMemo(
    () => ({ id, data, type: "rh" as const, position: { x: 0, y: 0 } }),
    [id, data],
  );

  const handleRun = useCallback(async () => {
    setRunning(true);
    try {
      await runRhNode(nodeRef, runtime);
      toast.success("RunningHub 任务完成");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "RunningHub 运行失败");
    } finally {
      setRunning(false);
    }
  }, [nodeRef, runtime]);

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
            onChange={(e) =>
              updateNodeData(
                id,
                rhMode === "workflow" ? { workflowId: e.target.value } : { webappId: e.target.value },
              )
            }
            placeholder="未配置"
            className="h-7 text-xs"
          />
        </div>
        <div>
          <Label className="text-xs text-muted-foreground">rhParams (JSON)</Label>
          <Textarea
            value={rhParamsJson}
            onChange={(e) => {
              try {
                const parsed = JSON.parse(e.target.value || "{}") as Record<string, unknown>;
                updateNodeData(id, { rhParams: parsed });
              } catch {
                /* 编辑中允许无效 JSON */
              }
            }}
            className="min-h-[72px] font-mono text-[10px]"
          />
        </div>
        {cascadeIdx ? <p className="text-xs text-muted-foreground">级联 {cascadeIdx}</p> : null}
        {runError ? <p className="text-xs text-destructive">{runError}</p> : null}
        <NodeRunActions
          nodeId={id}
          running={running}
          onRun={handleRun}
          runTestId={`canvas-rh-run-${id}`}
        />
      </div>
    </BaseNodeShell>
  );
}

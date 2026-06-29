import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCanvasEditorActions } from "../EditorActionsContext";
import { NodeRunActions } from "../NodeRunActions";
import { runMsGenNode, type RunNodeRuntime } from "../../lib/runNode";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { MsGenNodeData } from "@infinite-canvas/canvas-schema";

export function MsGenNode({ id, data, selected }: CanvasNodeProps<MsGenNodeData>) {
  const { nodes, edges, updateNodeData, appendLog, writeOutputImages } = useCanvasEditorActions();
  const [running, setRunning] = useState(Boolean(data.running));
  const modelKey = String(data.msgenModel ?? "zimage");
  const customModel = String(data.msCustomModel ?? "");
  const width = Number(data.msWidth ?? 1024);
  const height = Number(data.msHeight ?? 1024);
  const runError = String(data.runError ?? "");
  const cascadeIdx = String(data._cascadeIdx ?? "");

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
    () => ({ id, data, type: "msgen" as const, position: { x: 0, y: 0 } }),
    [id, data],
  );

  const handleRun = useCallback(async () => {
    setRunning(true);
    try {
      await runMsGenNode(nodeRef, runtime);
      toast.success("ModelScope 生成完成");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "ModelScope 生成失败");
    } finally {
      setRunning(false);
    }
  }, [nodeRef, runtime]);

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
        {cascadeIdx ? <p className="text-xs text-muted-foreground">级联 {cascadeIdx}</p> : null}
        {runError ? <p className="text-xs text-destructive">{runError}</p> : null}
        <NodeRunActions
          nodeId={id}
          running={running}
          onRun={handleRun}
          runTestId={`canvas-msgen-run-${id}`}
        />
      </div>
    </BaseNodeShell>
  );
}

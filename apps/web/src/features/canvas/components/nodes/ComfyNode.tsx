import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useCanvasEditorActions } from "../EditorActionsContext";
import { NodeRunActions } from "../NodeRunActions";
import { runComfyNode, type RunNodeRuntime } from "../../lib/runNode";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { ComfyNodeData } from "@infinite-canvas/canvas-schema";

const COMFY_MODES = ["text", "enhance", "edit", "custom"] as const;

export function ComfyNode({ id, data, selected }: CanvasNodeProps<ComfyNodeData>) {
  const { nodes, edges, updateNodeData, appendLog, writeOutputImages } = useCanvasEditorActions();
  const [running, setRunning] = useState(Boolean(data.running));
  const mode = String(data.mode ?? "text");
  const width = Number(data.width ?? 1024);
  const height = Number(data.height ?? 1024);
  const workflow = String(data.comfyWorkflow ?? "");
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
    () => ({ id, data, type: "comfy" as const, position: { x: 0, y: 0 } }),
    [id, data],
  );

  const handleRun = useCallback(async () => {
    setRunning(true);
    try {
      await runComfyNode(nodeRef, runtime);
      toast.success("ComfyUI 生成完成");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "ComfyUI 生成失败");
    } finally {
      setRunning(false);
    }
  }, [nodeRef, runtime]);

  return (
    <BaseNodeShell
      type="comfy"
      title="ComfyUI"
      selected={selected}
      running={running}
      data-testid={`canvas-node-${id}`}
    >
      <div className="space-y-2 nodrag">
        <div>
          <Label className="text-xs text-muted-foreground">模式</Label>
          <select
            className="flex h-7 w-full rounded-md border border-input bg-background px-2 text-xs"
            value={mode}
            onChange={(e) => updateNodeData(id, { mode: e.target.value })}
          >
            {COMFY_MODES.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>
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
        {mode === "custom" ? (
          <div>
            <Label className="text-xs text-muted-foreground">工作流 JSON</Label>
            <Textarea
              value={workflow}
              onChange={(e) => updateNodeData(id, { comfyWorkflow: e.target.value })}
              className="min-h-[60px] text-xs font-mono"
              placeholder="workflow.json 或 JSON"
            />
          </div>
        ) : null}
        {cascadeIdx ? <p className="text-xs text-muted-foreground">级联 {cascadeIdx}</p> : null}
        {runError ? <p className="text-xs text-destructive">{runError}</p> : null}
        <NodeRunActions
          nodeId={id}
          running={running}
          onRun={handleRun}
          runTestId={`canvas-comfy-run-${id}`}
        />
      </div>
    </BaseNodeShell>
  );
}

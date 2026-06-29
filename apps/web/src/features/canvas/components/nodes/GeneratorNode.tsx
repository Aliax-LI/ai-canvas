import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCanvasEditorActions } from "../EditorActionsContext";
import { NodeRunActions } from "../NodeRunActions";
import { runGeneratorNode, type RunNodeRuntime } from "../../lib/runNode";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { GeneratorNodeData } from "@infinite-canvas/canvas-schema";

export function GeneratorNode({ id, data, selected }: CanvasNodeProps<GeneratorNodeData>) {
  const { nodes, edges, updateNodeData, getRunContext, appendLog, writeOutputImages } =
    useCanvasEditorActions();
  const [running, setRunning] = useState(Boolean(data.running));
  const provider = String(data.apiProvider ?? "comfly");
  const model = String(data.model ?? "");
  const ratio = String(data.ratio ?? "square");
  const resolution = String(data.resolution ?? "1k");
  const runStatus = String(data.runStatus ?? "");
  const runError = String(data.runError ?? "");
  const cascadeIdx = String(data._cascadeIdx ?? "");

  const runContext = useMemo(() => getRunContext(id), [getRunContext, id, nodes, edges]);
  const promptPreview = runContext.prompt;

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
    () => ({ id, data, type: "generator" as const, position: { x: 0, y: 0 } }),
    [id, data],
  );

  const handleRun = useCallback(async () => {
    setRunning(true);
    try {
      await runGeneratorNode(nodeRef, runtime);
      toast.success("生成完成");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "生成失败";
      toast.error(msg);
    } finally {
      setRunning(false);
    }
  }, [nodeRef, runtime]);

  return (
    <BaseNodeShell
      type="generator"
      title="API 生图"
      selected={selected}
      running={running || runStatus === "running"}
      error={runStatus === "failed"}
      data-testid={`canvas-node-${id}`}
    >
      <div className="space-y-2 nodrag">
        {promptPreview ? (
          <p
            className="line-clamp-2 rounded bg-muted/50 px-2 py-1 text-xs text-muted-foreground"
            data-testid="canvas-generator-prompt-preview"
          >
            {promptPreview}
          </p>
        ) : null}
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
        {cascadeIdx ? (
          <p className="text-xs text-muted-foreground">级联 {cascadeIdx}</p>
        ) : null}
        {runError ? <p className="text-xs text-destructive">{runError}</p> : null}
        <NodeRunActions
          nodeId={id}
          running={running}
          onRun={handleRun}
          runTestId={`canvas-generator-run-${id}`}
        />
      </div>
    </BaseNodeShell>
  );
}

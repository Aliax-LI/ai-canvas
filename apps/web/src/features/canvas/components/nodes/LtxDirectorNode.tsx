import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { useCanvasEditorActions } from "../EditorActionsContext";
import { GeneratorInputList } from "../GeneratorInputList";
import { LtxTimeline } from "../LtxTimeline";
import { NodeRunActions } from "../NodeRunActions";
import { ltxSyncConnectedImagesToTimeline } from "../../lib/ltx";
import { orderedSources, reorderInput } from "../../lib/graph";
import { runLtxDirectorNode, type RunNodeRuntime } from "../../lib/runNode";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { LtxDirectorNodeData } from "@infinite-canvas/canvas-schema";

export function LtxDirectorNode({ id, data, selected }: CanvasNodeProps<LtxDirectorNodeData>) {
  const { nodes, edges, updateNodeData, appendLog, writeOutputImages } = useCanvasEditorActions();
  const [running, setRunning] = useState(Boolean(data.running));
  const runError = String(data.runError ?? "");
  const cascadeIdx = String(data._cascadeIdx ?? "");
  const inputs = Array.isArray(data.inputs) ? (data.inputs as string[]) : [];

  const sources = useMemo(
    () => orderedSources(id, data as Record<string, unknown>, nodes, edges),
    [id, data, nodes, edges],
  );

  useEffect(() => {
    const node = nodes.find((n) => n.id === id);
    if (!node) return;
    const { patch } = ltxSyncConnectedImagesToTimeline(node, nodes, edges);
    if (Object.keys(patch).length) updateNodeData(id, patch);
  }, [id, nodes, edges, updateNodeData]);

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
    () => ({ id, data, type: "ltxDirector" as const, position: { x: 0, y: 0 } }),
    [id, data],
  );

  const handleReorder = useCallback(
    (movedId: string, targetId: string) => {
      const next = reorderInput(id, data as Record<string, unknown>, nodes, edges, movedId, targetId);
      if (!next) return;
      updateNodeData(id, { inputs: next });
      const node = nodes.find((n) => n.id === id);
      if (node) {
        const { patch } = ltxSyncConnectedImagesToTimeline(
          { ...node, data: { ...node.data, inputs: next } },
          nodes,
          edges,
        );
        updateNodeData(id, { ...patch, inputs: next });
      }
    },
    [id, data, nodes, edges, updateNodeData],
  );

  const handleRun = useCallback(async () => {
    setRunning(true);
    try {
      await runLtxDirectorNode(nodeRef, runtime);
      toast.success("LTX Director 完成");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "LTX 运行失败");
    } finally {
      setRunning(false);
    }
  }, [nodeRef, runtime]);

  return (
    <BaseNodeShell
      type="ltxDirector"
      title="LTX Director"
      selected={selected}
      running={running}
      className="min-w-[300px] max-w-[360px]"
      data-testid={`canvas-node-${id}`}
    >
      <div className="space-y-2 nodrag">
        <GeneratorInputList
          nodeId={id}
          sources={sources}
          inputs={inputs}
          onReorder={handleReorder}
        />
        <LtxTimeline
          nodeId={id}
          data={data as Record<string, unknown>}
          onUpdate={(patch) => updateNodeData(id, patch)}
        />
        {cascadeIdx ? <p className="text-xs text-muted-foreground">级联 {cascadeIdx}</p> : null}
        {runError ? <p className="text-xs text-destructive">{runError}</p> : null}
        <NodeRunActions
          nodeId={id}
          running={running}
          onRun={handleRun}
          runTestId={`canvas-ltx-run-${id}`}
        />
      </div>
    </BaseNodeShell>
  );
}

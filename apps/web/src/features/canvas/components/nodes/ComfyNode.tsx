import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useCanvasEditorActions } from "../EditorActionsContext";
import { GeneratorInputList } from "../GeneratorInputList";
import { NodeRunActions } from "../NodeRunActions";
import { orderedSources, reorderInput } from "../../lib/graph";
import { runComfyNode, type RunNodeRuntime } from "../../lib/runNode";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { ComfyNodeData } from "@infinite-canvas/canvas-schema";

const COMFY_MODES = ["text", "enhance", "edit", "custom"] as const;
const RATIO_OPTIONS = ["1:1", "3:4", "4:3", "16:9", "9:16"];
const RES_OPTIONS = ["1k", "2k", "4k"];

export function ComfyNode({ id, data, selected }: CanvasNodeProps<ComfyNodeData>) {
  const { nodes, edges, updateNodeData, appendLog, writeOutputImages } = useCanvasEditorActions();
  const [running, setRunning] = useState(Boolean(data.running));
  const mode = String(data.mode ?? "text");
  const width = Number(data.width ?? 1024);
  const height = Number(data.height ?? 1024);
  const ratio = String(data.ratio ?? "1:1");
  const resolution = String(data.resolution ?? "1k");
  const workflow = String(data.comfyWorkflow ?? "");
  const enhanceStrength = Number(data.enhanceStrength ?? 0.5);
  const enhanceUpscale = Boolean(data.enhanceUpscale);
  const enhanceUpscaleRes = Number(data.enhanceUpscaleRes ?? 2048);
  const editUpscale = Boolean(data.editUpscale);
  const editUpscaleRes = Number(data.editUpscaleRes ?? 2048);
  const editModel = String(data.editModel ?? "");
  const runError = String(data.runError ?? "");
  const cascadeIdx = String(data._cascadeIdx ?? "");
  const inputs = Array.isArray(data.inputs) ? (data.inputs as string[]) : [];

  const sources = useMemo(
    () => orderedSources(id, data as Record<string, unknown>, nodes, edges),
    [id, data, nodes, edges],
  );

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

  const handleReorder = useCallback(
    (movedId: string, targetId: string) => {
      const next = reorderInput(id, data as Record<string, unknown>, nodes, edges, movedId, targetId);
      if (next) updateNodeData(id, { inputs: next });
    },
    [id, data, nodes, edges, updateNodeData],
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
        <GeneratorInputList
          nodeId={id}
          sources={sources}
          inputs={inputs}
          onReorder={handleReorder}
        />
        {mode === "text" ? (
          <>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-xs text-muted-foreground">宽</Label>
                <Input
                  type="number"
                  value={String(width)}
                  className="h-7 text-xs"
                  onChange={(e) => updateNodeData(id, { width: Number(e.target.value) || 1024 })}
                />
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">高</Label>
                <Input
                  type="number"
                  value={String(height)}
                  className="h-7 text-xs"
                  onChange={(e) => updateNodeData(id, { height: Number(e.target.value) || 1024 })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-xs text-muted-foreground">比例</Label>
                <select
                  className="flex h-7 w-full rounded-md border border-input bg-background px-2 text-xs"
                  value={ratio}
                  onChange={(e) => updateNodeData(id, { ratio: e.target.value })}
                >
                  {RATIO_OPTIONS.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">分辨率</Label>
                <select
                  className="flex h-7 w-full rounded-md border border-input bg-background px-2 text-xs"
                  value={resolution}
                  onChange={(e) => updateNodeData(id, { resolution: e.target.value })}
                >
                  {RES_OPTIONS.map((r) => (
                    <option key={r} value={r}>
                      {r.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </>
        ) : null}
        {mode === "enhance" ? (
          <>
            <div>
              <Label className="text-xs text-muted-foreground">
                增强强度 ({enhanceStrength.toFixed(2)})
              </Label>
              <Input
                type="range"
                min={0.1}
                max={1}
                step={0.05}
                value={enhanceStrength}
                className="h-7"
                onChange={(e) => updateNodeData(id, { enhanceStrength: Number(e.target.value) })}
              />
            </div>
            <label className="flex items-center gap-2 text-xs">
              <input
                type="checkbox"
                checked={enhanceUpscale}
                onChange={(e) => updateNodeData(id, { enhanceUpscale: e.target.checked })}
              />
              超分辨率
            </label>
            {enhanceUpscale ? (
              <select
                className="flex h-7 w-full rounded-md border border-input bg-background px-2 text-xs"
                value={String(enhanceUpscaleRes)}
                onChange={(e) => updateNodeData(id, { enhanceUpscaleRes: Number(e.target.value) })}
              >
                <option value="2048">2X (2048)</option>
                <option value="4096">4X (4096)</option>
              </select>
            ) : null}
          </>
        ) : null}
        {mode === "edit" ? (
          <>
            <div>
              <Label className="text-xs text-muted-foreground">编辑模型</Label>
              <Input
                value={editModel}
                className="h-7 text-xs"
                placeholder="模型 ID"
                onChange={(e) => updateNodeData(id, { editModel: e.target.value })}
              />
            </div>
            <label className="flex items-center gap-2 text-xs">
              <input
                type="checkbox"
                checked={editUpscale}
                onChange={(e) => updateNodeData(id, { editUpscale: e.target.checked })}
              />
              超分辨率
            </label>
            {editUpscale ? (
              <select
                className="flex h-7 w-full rounded-md border border-input bg-background px-2 text-xs"
                value={String(editUpscaleRes)}
                onChange={(e) => updateNodeData(id, { editUpscaleRes: Number(e.target.value) })}
              >
                <option value="2048">2X (2048)</option>
                <option value="4096">4X (4096)</option>
              </select>
            ) : null}
          </>
        ) : null}
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

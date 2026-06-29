import { useCallback, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createCanvasComfyTask, newCanvasClientId } from "../../api";
import { useCanvasEditorActions } from "../EditorActionsContext";
import { defaultRunPrompt, findDownstreamOutput, needPromptOrImage } from "../../lib/graph";
import { waitForComfyTask } from "../../lib/nodeRun";
import { mergeGeneratedOutputs } from "../../lib/runHelpers";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { ComfyNodeData } from "@infinite-canvas/canvas-schema";

export function ComfyNode({ id, data, selected }: CanvasNodeProps<ComfyNodeData>) {
  const { nodes, edges, updateNodeData, getRunContext, appendLog, writeOutputImages } =
    useCanvasEditorActions();
  const [running, setRunning] = useState(Boolean(data.running));
  const mode = String(data.mode ?? "text");
  const width = Number(data.width ?? 1024);
  const height = Number(data.height ?? 1024);
  const workflow = String(data.comfyWorkflow ?? "");
  const runError = String(data.runError ?? "");
  const generatedOutputs = (data as { generatedOutputs?: unknown[] }).generatedOutputs;

  const handleRun = useCallback(async () => {
    const { prompt, referenceImages } = getRunContext(id);
    if (!needPromptOrImage(prompt, referenceImages)) {
      toast.error("请连接提示词或参考图");
      return;
    }

    setRunning(true);
    updateNodeData(id, { running: true, runStatus: "running", runError: "" });
    appendLog({ nodeId: id, nodeType: "comfy", status: "running" });

    try {
      const effectivePrompt = defaultRunPrompt(prompt);
      const task = await createCanvasComfyTask({
        prompt: effectivePrompt,
        width,
        height,
        workflow_json: mode === "custom" && workflow ? workflow : "Z-Image.json",
        type: mode === "text" ? "zimage" : "workflow",
        client_id: newCanvasClientId(),
      });
      const result = await waitForComfyTask(task.task_id);
      const images = result.images ?? [];
      if (images.length) {
        const outputs = mergeGeneratedOutputs(generatedOutputs, images);
        updateNodeData(id, { generatedOutputs: outputs });
        const outNode = findDownstreamOutput(id, nodes, edges);
        if (outNode) writeOutputImages(outNode.id, images);
      }
      updateNodeData(id, { running: false, runStatus: "succeeded" });
      appendLog({ nodeId: id, nodeType: "comfy", status: "succeeded", message: "ComfyUI 完成" });
      toast.success("ComfyUI 生成完成");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "ComfyUI 生成失败";
      updateNodeData(id, { running: false, runStatus: "failed", runError: msg });
      appendLog({ nodeId: id, nodeType: "comfy", status: "failed", message: msg });
      toast.error(msg);
    } finally {
      setRunning(false);
    }
  }, [
    id,
    getRunContext,
    mode,
    width,
    height,
    workflow,
    generatedOutputs,
    nodes,
    edges,
    updateNodeData,
    appendLog,
    writeOutputImages,
  ]);

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
          <Input value={mode} readOnly className="h-7 text-xs" />
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
        {workflow ? (
          <div>
            <Label className="text-xs text-muted-foreground">工作流</Label>
            <Input value={workflow} readOnly className="h-7 text-xs" />
          </div>
        ) : null}
        {runError ? <p className="text-xs text-destructive">{runError}</p> : null}
        <Button
          type="button"
          size="sm"
          className="w-full"
          disabled={running}
          data-testid={`canvas-comfy-run-${id}`}
          onClick={() => void handleRun()}
        >
          {running ? <Loader2 className="mr-1 size-3 animate-spin" /> : <Play className="mr-1 size-3" />}
          运行
        </Button>
      </div>
    </BaseNodeShell>
  );
}

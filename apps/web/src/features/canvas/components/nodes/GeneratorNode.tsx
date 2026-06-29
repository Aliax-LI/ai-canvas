import { useCallback, useMemo, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createCanvasImageTask } from "../../api";
import { useCanvasEditorActions } from "../EditorActionsContext";
import { defaultRunPrompt, findDownstreamOutput, needPromptOrImage } from "../../lib/graph";
import { waitForImageTask } from "../../lib/nodeRun";
import { mergeGeneratedOutputs } from "../../lib/runHelpers";
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

  const runContext = useMemo(() => getRunContext(id), [getRunContext, id, nodes, edges]);
  const promptPreview = runContext.prompt;

  const handleRun = useCallback(async () => {
    const { prompt, referenceImages } = getRunContext(id);
    if (!needPromptOrImage(prompt, referenceImages)) {
      toast.error("请连接提示词或参考图");
      return;
    }

    setRunning(true);
    updateNodeData(id, { running: true, runStatus: "running", runError: "" });
    appendLog({ nodeId: id, nodeType: "generator", status: "running", message: "开始生成" });

    try {
      const effectivePrompt = defaultRunPrompt(prompt);
      const task = await createCanvasImageTask({
        prompt: effectivePrompt,
        provider_id: provider,
        model: model || "dall-e-3",
        size: resolution === "1k" ? "1024x1024" : "512x512",
        reference_images: referenceImages.map((r) => ({ url: r.url, name: r.name })),
      });
      const images = await waitForImageTask(task.task_id);
      const outputs = mergeGeneratedOutputs(data.generatedOutputs, images);
      updateNodeData(id, {
        running: false,
        runStatus: "succeeded",
        generatedOutputs: outputs,
      });
      const outNode = findDownstreamOutput(id, nodes, edges);
      if (outNode) writeOutputImages(outNode.id, images);
      appendLog({
        nodeId: id,
        nodeType: "generator",
        status: "succeeded",
        message: `生成 ${images.length} 张图`,
      });
      toast.success("生成完成");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "生成失败";
      updateNodeData(id, { running: false, runStatus: "failed", runError: msg });
      appendLog({ nodeId: id, nodeType: "generator", status: "failed", message: msg });
      toast.error(msg);
    } finally {
      setRunning(false);
    }
  }, [
    id,
    getRunContext,
    provider,
    model,
    resolution,
    data.generatedOutputs,
    nodes,
    edges,
    updateNodeData,
    appendLog,
    writeOutputImages,
  ]);

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

import { useCallback, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { msGenerate, newCanvasClientId } from "../../api";
import { useCanvasEditorActions } from "../EditorActionsContext";
import { defaultRunPrompt, findDownstreamOutput, needPromptOrImage } from "../../lib/graph";
import { mergeGeneratedOutputs } from "../../lib/runHelpers";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { MsGenNodeData } from "@infinite-canvas/canvas-schema";

export function MsGenNode({ id, data, selected }: CanvasNodeProps<MsGenNodeData>) {
  const { nodes, edges, updateNodeData, getRunContext, appendLog, writeOutputImages } =
    useCanvasEditorActions();
  const [running, setRunning] = useState(Boolean(data.running));
  const modelKey = String(data.msgenModel ?? "zimage");
  const customModel = String(data.msCustomModel ?? "");
  const width = Number(data.msWidth ?? 1024);
  const height = Number(data.msHeight ?? 1024);
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
    appendLog({ nodeId: id, nodeType: "msgen", status: "running" });

    try {
      const effectivePrompt = defaultRunPrompt(prompt);
      const imageUrls = referenceImages.map((r) => r.url);
      const payload =
        modelKey === "zimage"
          ? {
              prompt: effectivePrompt,
              resolution: `${width}x${height}`,
              image_urls: imageUrls.length ? imageUrls : undefined,
              client_id: newCanvasClientId(),
            }
          : {
              prompt: effectivePrompt,
              model: customModel || "Tongyi-MAI/Z-Image-Turbo",
              width,
              height,
              size: `${width}x${height}`,
              image_urls: imageUrls.length ? imageUrls : undefined,
              client_id: newCanvasClientId(),
            };
      const result = await msGenerate(payload);
      const urls = result.url ? [result.url] : [];
      if (urls.length) {
        const outputs = mergeGeneratedOutputs(generatedOutputs, urls);
        updateNodeData(id, { generatedOutputs: outputs });
        const outNode = findDownstreamOutput(id, nodes, edges);
        if (outNode) writeOutputImages(outNode.id, urls);
      }
      updateNodeData(id, { running: false, runStatus: "succeeded" });
      appendLog({ nodeId: id, nodeType: "msgen", status: "succeeded", message: "ModelScope 完成" });
      toast.success(urls.length ? "ModelScope 生成完成" : "ModelScope 任务已提交");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "ModelScope 生成失败";
      updateNodeData(id, { running: false, runStatus: "failed", runError: msg });
      appendLog({ nodeId: id, nodeType: "msgen", status: "failed", message: msg });
      toast.error(msg);
    } finally {
      setRunning(false);
    }
  }, [
    id,
    getRunContext,
    modelKey,
    customModel,
    width,
    height,
    generatedOutputs,
    nodes,
    edges,
    updateNodeData,
    appendLog,
    writeOutputImages,
  ]);

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
        {runError ? <p className="text-xs text-destructive">{runError}</p> : null}
        <Button
          type="button"
          size="sm"
          className="w-full"
          disabled={running}
          data-testid={`canvas-msgen-run-${id}`}
          onClick={() => void handleRun()}
        >
          {running ? <Loader2 className="mr-1 size-3 animate-spin" /> : <Play className="mr-1 size-3" />}
          运行
        </Button>
      </div>
    </BaseNodeShell>
  );
}

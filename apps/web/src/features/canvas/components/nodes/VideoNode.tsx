import { useCallback, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createCanvasVideo } from "../../api";
import { useCanvasEditorActions } from "../EditorActionsContext";
import { defaultRunPrompt, findDownstreamOutput, needPromptOrImage } from "../../lib/graph";
import { mergeGeneratedOutputs } from "../../lib/runHelpers";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { VideoNodeData } from "@infinite-canvas/canvas-schema";

export function VideoNode({ id, data, selected }: CanvasNodeProps<VideoNodeData>) {
  const { nodes, edges, updateNodeData, getRunContext, appendLog, writeOutputImages } =
    useCanvasEditorActions();
  const [running, setRunning] = useState(Boolean(data.running));
  const provider = String(data.apiProvider ?? "comfly");
  const model = String(data.model ?? "veo3-fast");
  const duration = Number(data.duration ?? 5);
  const aspectRatio = String(data.aspectRatio ?? "16:9");
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
    appendLog({ nodeId: id, nodeType: "video", status: "running" });

    try {
      const effectivePrompt = defaultRunPrompt(prompt);
      const result = await createCanvasVideo({
        prompt: effectivePrompt,
        provider_id: provider,
        model,
        duration,
        aspect_ratio: aspectRatio,
        enhance_prompt: Boolean(data.enhancePrompt),
        generate_audio: Boolean(data.generateAudio),
        multimodal: Boolean(data.multimodal),
      });
      const urls = result.urls ?? (result.url ? [result.url] : result.video ? [result.video] : []);
      if (urls.length) {
        const outputs = mergeGeneratedOutputs(generatedOutputs, urls, "video");
        updateNodeData(id, { generatedOutputs: outputs });
        const outNode = findDownstreamOutput(id, nodes, edges);
        if (outNode) writeOutputImages(outNode.id, urls);
      }
      updateNodeData(id, { running: false, runStatus: "succeeded" });
      appendLog({ nodeId: id, nodeType: "video", status: "succeeded", message: "视频生成完成" });
      toast.success("视频生成完成");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "视频生成失败";
      updateNodeData(id, { running: false, runStatus: "failed", runError: msg });
      appendLog({ nodeId: id, nodeType: "video", status: "failed", message: msg });
      toast.error(msg);
    } finally {
      setRunning(false);
    }
  }, [
    id,
    getRunContext,
    provider,
    model,
    duration,
    aspectRatio,
    data.enhancePrompt,
    data.generateAudio,
    data.multimodal,
    generatedOutputs,
    nodes,
    edges,
    updateNodeData,
    appendLog,
    writeOutputImages,
  ]);

  return (
    <BaseNodeShell
      type="video"
      title="视频生成"
      selected={selected}
      running={running}
      data-testid={`canvas-node-${id}`}
    >
      <div className="space-y-2 nodrag">
        <div>
          <Label className="text-xs text-muted-foreground">平台</Label>
          <Input value={provider} readOnly className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs text-muted-foreground">模型</Label>
          <Input value={model} readOnly className="h-7 text-xs" />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <Label className="text-xs text-muted-foreground">时长</Label>
            <Input value={`${duration}s`} readOnly className="h-7 text-xs" />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">比例</Label>
            <Input value={aspectRatio} readOnly className="h-7 text-xs" />
          </div>
        </div>
        {runError ? <p className="text-xs text-destructive">{runError}</p> : null}
        <Button
          type="button"
          size="sm"
          className="w-full"
          disabled={running}
          data-testid={`canvas-video-run-${id}`}
          onClick={() => void handleRun()}
        >
          {running ? <Loader2 className="mr-1 size-3 animate-spin" /> : <Play className="mr-1 size-3" />}
          运行
        </Button>
      </div>
    </BaseNodeShell>
  );
}

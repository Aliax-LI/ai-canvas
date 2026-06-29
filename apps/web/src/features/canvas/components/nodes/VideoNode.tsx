import { useCallback, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createCanvasVideo } from "../../api";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { VideoNodeData } from "@infinite-canvas/canvas-schema";

export function VideoNode({ id, data, selected }: CanvasNodeProps<VideoNodeData>) {
  const [running, setRunning] = useState(Boolean(data.running));
  const provider = String(data.apiProvider ?? "comfly");
  const model = String(data.model ?? "veo3-fast");
  const duration = Number(data.duration ?? 5);
  const aspectRatio = String(data.aspectRatio ?? "16:9");
  const runError = String(data.runError ?? "");

  const handleRun = useCallback(async () => {
    setRunning(true);
    try {
      await createCanvasVideo({
        prompt: "A cinematic landscape video",
        provider_id: provider,
        model,
        duration,
        aspect_ratio: aspectRatio,
        enhance_prompt: Boolean(data.enhancePrompt),
        generate_audio: Boolean(data.generateAudio),
        multimodal: Boolean(data.multimodal),
      });
      toast.success("视频生成完成");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "视频生成失败");
    } finally {
      setRunning(false);
    }
  }, [provider, model, duration, aspectRatio, data.enhancePrompt, data.generateAudio, data.multimodal]);

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

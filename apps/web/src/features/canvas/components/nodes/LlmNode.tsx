import { useCallback, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createCanvasLlm } from "../../api";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { LlmNodeData } from "@infinite-canvas/canvas-schema";

export function LlmNode({ id, data, selected }: CanvasNodeProps<LlmNodeData>) {
  const [running, setRunning] = useState(Boolean(data.running));
  const provider = String(data.llmProvider ?? "comfly");
  const model = String(data.model ?? "");
  const outputText = String(data.outputText ?? "");
  const runError = String(data.runError ?? "");

  const handleRun = useCallback(async () => {
    setRunning(true);
    try {
      const result = await createCanvasLlm({
        message: data.chatInput || "Rewrite this into an image prompt",
        system_prompt: String(data.systemPrompt ?? ""),
        model,
        provider,
      });
      toast.success(result.text ? "LLM 完成" : "LLM 已响应");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "LLM 运行失败");
    } finally {
      setRunning(false);
    }
  }, [data.chatInput, data.systemPrompt, model, provider]);

  return (
    <BaseNodeShell
      type="llm"
      title="LLM"
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
          <Input value={model} readOnly placeholder="默认模型" className="h-7 text-xs" />
        </div>
        {outputText ? (
          <p className="line-clamp-3 text-xs text-muted-foreground">{outputText}</p>
        ) : null}
        {runError ? <p className="text-xs text-destructive">{runError}</p> : null}
        <Button
          type="button"
          size="sm"
          className="w-full"
          disabled={running}
          data-testid={`canvas-llm-run-${id}`}
          onClick={() => void handleRun()}
        >
          {running ? <Loader2 className="mr-1 size-3 animate-spin" /> : <Play className="mr-1 size-3" />}
          运行
        </Button>
      </div>
    </BaseNodeShell>
  );
}

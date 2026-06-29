import { useCallback, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createCanvasLlm } from "../../api";
import { useCanvasEditorActions } from "../EditorActionsContext";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { LlmNodeData } from "@infinite-canvas/canvas-schema";

export function LlmNode({ id, data, selected }: CanvasNodeProps<LlmNodeData>) {
  const { nodes, edges, getRunContext, updateNodeData, appendLog } = useCanvasEditorActions();
  const [running, setRunning] = useState(Boolean(data.running));
  const provider = String(data.llmProvider ?? "comfly");
  const model = String(data.model ?? "");
  const outputText = String(data.outputText ?? "");
  const runError = String(data.runError ?? "");

  const handleRun = useCallback(async () => {
    const { prompt } = getRunContext(id);
    const message = prompt.trim() || String(data.chatInput ?? "").trim() || "Rewrite this into an image prompt";

    setRunning(true);
    updateNodeData(id, { running: true, runStatus: "running", runError: "" });
    appendLog({ nodeId: id, nodeType: "llm", status: "running" });

    try {
      const result = await createCanvasLlm({
        message,
        system_prompt: String(data.systemPrompt ?? ""),
        model,
        provider,
      });
      const text = result.text ?? "";
      updateNodeData(id, {
        running: false,
        runStatus: "succeeded",
        outputText: text,
      });
      appendLog({
        nodeId: id,
        nodeType: "llm",
        status: "succeeded",
        message: text ? text.slice(0, 48) : "LLM 已响应",
      });
      toast.success(text ? "LLM 完成" : "LLM 已响应");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "LLM 运行失败";
      updateNodeData(id, { running: false, runStatus: "failed", runError: msg });
      appendLog({ nodeId: id, nodeType: "llm", status: "failed", message: msg });
      toast.error(msg);
    } finally {
      setRunning(false);
    }
  }, [id, getRunContext, data.chatInput, data.systemPrompt, model, provider, updateNodeData, appendLog, nodes, edges]);

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

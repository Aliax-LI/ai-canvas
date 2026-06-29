import { useCallback, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCanvasEditorActions } from "../EditorActionsContext";
import { renderLoopPrompt } from "../../lib/graph";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { LoopNodeData } from "@infinite-canvas/canvas-schema";

export function LoopNode({ id, data, selected }: CanvasNodeProps<LoopNodeData>) {
  const { nodes, edges, updateNodeData, appendLog } = useCanvasEditorActions();
  const [running, setRunning] = useState(Boolean(data.running));
  const count = Number(data.count ?? 3);
  const mode = String(data.mode ?? "serial");

  const handleRun = useCallback(async () => {
    setRunning(true);
    updateNodeData(id, { running: true, runStatus: "running", runError: "" });
    appendLog({ nodeId: id, nodeType: "loop", status: "running", message: `循环 ${count} 次` });

    try {
      const loopNode = nodes.find((n) => n.id === id);
      if (!loopNode) throw new Error("节点不存在");

      for (let i = 1; i <= count; i++) {
        const ctx = { index: i, total: count };
        const prompt = renderLoopPrompt(loopNode, nodes, edges, ctx);
        appendLog({
          nodeId: id,
          nodeType: "loop",
          status: "running",
          message: `[${i}/${count}] ${prompt.slice(0, 64) || "(空提示词)"}`,
        });
        if (mode === "serial") {
          await new Promise((r) => setTimeout(r, 120));
        }
      }

      updateNodeData(id, { running: false, runStatus: "succeeded" });
      appendLog({ nodeId: id, nodeType: "loop", status: "succeeded", message: `完成 ${count} 轮` });
      toast.success(`循环完成 ${count} 轮`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "循环运行失败";
      updateNodeData(id, { running: false, runStatus: "failed", runError: msg });
      appendLog({ nodeId: id, nodeType: "loop", status: "failed", message: msg });
      toast.error(msg);
    } finally {
      setRunning(false);
    }
  }, [id, count, mode, nodes, edges, updateNodeData, appendLog]);

  return (
    <BaseNodeShell
      type="loop"
      title="循环"
      selected={selected}
      running={running}
      data-testid={`canvas-node-${id}`}
    >
      <div className="space-y-2 nodrag">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <Label className="text-xs text-muted-foreground">次数</Label>
            <Input value={String(count)} readOnly className="h-7 text-xs" />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">模式</Label>
            <Input value={mode} readOnly className="h-7 text-xs" />
          </div>
        </div>
        <Button
          type="button"
          size="sm"
          className="w-full"
          disabled={running}
          data-testid={`canvas-loop-run-${id}`}
          onClick={() => void handleRun()}
        >
          {running ? <Loader2 className="mr-1 size-3 animate-spin" /> : <Play className="mr-1 size-3" />}
          运行
        </Button>
      </div>
    </BaseNodeShell>
  );
}

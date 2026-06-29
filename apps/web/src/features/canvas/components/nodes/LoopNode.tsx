import { useCallback, useMemo } from "react";
import { GitBranch, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCanvasEditorActions } from "../EditorActionsContext";
import {
  computeCascadeOrder,
  findLoopCascadeTarget,
} from "../../lib/cascade";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { LoopNodeData } from "@infinite-canvas/canvas-schema";

export function LoopNode({ id, data, selected }: CanvasNodeProps<LoopNodeData>) {
  const { nodes, edges, runCascade, cascadeRunning, updateNodeData } = useCanvasEditorActions();
  const count = Number(data.count ?? 3);
  const mode = String(data.mode ?? "serial");
  const runError = String(data.runError ?? "");
  const cascadeIdx = String(data._cascadeIdx ?? "");

  const loopTargetId = useMemo(
    () => findLoopCascadeTarget(id, nodes, edges),
    [id, nodes, edges],
  );
  const orderLen = useMemo(
    () => (loopTargetId ? computeCascadeOrder(loopTargetId, nodes, edges).length : 0),
    [loopTargetId, nodes, edges],
  );

  const handleCascade = useCallback(async () => {
    if (!loopTargetId) {
      toast.error("请连接下游生成器");
      return;
    }
    try {
      await runCascade(loopTargetId);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "级联运行失败");
    }
  }, [loopTargetId, runCascade]);

  return (
    <BaseNodeShell
      type="loop"
      title="循环"
      selected={selected}
      running={cascadeRunning}
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
            <select
              className="flex h-7 w-full rounded-md border border-input bg-background px-2 text-xs"
              value={mode}
              onChange={(e) => updateNodeData(id, { mode: e.target.value })}
              data-testid={`canvas-loop-mode-${id}`}
            >
              <option value="serial">串行</option>
              <option value="parallel">并行</option>
            </select>
          </div>
        </div>
        {loopTargetId ? (
          <p className="text-xs text-muted-foreground">
            下游 {orderLen || 1} 个节点 × {count} 轮
          </p>
        ) : (
          <p className="text-xs text-muted-foreground">未连接下游生成器</p>
        )}
        {cascadeIdx ? <p className="text-xs text-muted-foreground">级联 {cascadeIdx}</p> : null}
        {runError ? <p className="text-xs text-destructive">{runError}</p> : null}
        <Button
          type="button"
          size="sm"
          className="w-full"
          disabled={!loopTargetId || cascadeRunning}
          data-testid={`canvas-loop-cascade-${id}`}
          onClick={() => void handleCascade()}
        >
          {cascadeRunning ? (
            <Loader2 className="mr-1 size-3 animate-spin" />
          ) : (
            <GitBranch className="mr-1 size-3" />
          )}
          级联运行
        </Button>
      </div>
    </BaseNodeShell>
  );
}

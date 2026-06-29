import { useMemo } from "react";
import { GitBranch } from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useCanvasEditorActions } from "../EditorActionsContext";
import { generatorSources } from "../../lib/graph";
import { findLoopCascadeTarget, resolveCascadeTargetId } from "../../lib/cascade";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { PromptGroupNodeData } from "@infinite-canvas/canvas-schema";

export function PromptGroupNode({ id, data, selected }: CanvasNodeProps<PromptGroupNodeData>) {
  const { nodes, edges, runCascade } = useCanvasEditorActions();
  const items = Array.isArray(data.items) ? data.items : [];

  const aggregatedPrompt = useMemo(() => {
    const sources = generatorSources(id, nodes, edges);
    return sources.find((s) => s.type === "promptGroup")?.prompt ?? "";
  }, [id, nodes, edges]);

  const downstreamTarget = useMemo(() => {
    for (const edge of edges.filter((e) => e.source === id)) {
      const target = resolveCascadeTargetId(edge.target, nodes, edges);
      if (target) return target;
    }
    return findLoopCascadeTarget(id, nodes, edges);
  }, [id, nodes, edges]);

  return (
    <BaseNodeShell
      type="promptGroup"
      title="提示词组"
      selected={selected}
      data-testid={`canvas-node-${id}`}
    >
      <div className="space-y-2 nodrag">
        <div>
          <Label className="text-xs text-muted-foreground">成员数</Label>
          <Input value={String(items.length)} readOnly className="h-7 text-xs" />
        </div>
        {aggregatedPrompt ? (
          <p
            className="line-clamp-3 rounded bg-muted/50 px-2 py-1 text-xs text-muted-foreground"
            data-testid={`canvas-promptgroup-preview-${id}`}
          >
            {aggregatedPrompt}
          </p>
        ) : null}
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="w-full"
          data-testid={`canvas-promptgroup-run-${id}`}
          onClick={() => {
            if (downstreamTarget) {
              void runCascade(downstreamTarget);
              return;
            }
            toast.info(
              aggregatedPrompt
                ? `已聚合 ${items.length} 条提示词，请连接到生成器后运行`
                : "暂无提示词成员",
            );
          }}
        >
          <GitBranch className="mr-1 size-3" />
          {downstreamTarget ? "级联运行" : "预览"}
        </Button>
      </div>
    </BaseNodeShell>
  );
}

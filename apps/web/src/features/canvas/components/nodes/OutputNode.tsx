import { CircleDot, GitBranch } from "lucide-react";
import { Button } from "@/components/ui/button";
import { mediaPreviewUrl } from "../../api";
import { useCanvasEditorActions } from "../EditorActionsContext";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { OutputNodeData } from "@infinite-canvas/canvas-schema";

export function OutputNode({ id, data, selected }: CanvasNodeProps<OutputNodeData>) {
  const { runCascade, cascadeRunning } = useCanvasEditorActions();
  const images = Array.isArray(data.images) ? data.images : [];
  const last = images[images.length - 1];

  return (
    <BaseNodeShell
      type="output"
      title="输出"
      selected={selected}
      data-testid={`canvas-node-${id}`}
    >
      {last?.url ? (
        <img
          src={mediaPreviewUrl(String(last.url), 400)}
          alt={String(last.name ?? "output")}
          className="max-h-32 w-full rounded-md object-cover"
        />
      ) : (
        <div className="flex h-24 items-center justify-center rounded-md bg-muted text-muted-foreground">
          <CircleDot className="size-8" strokeWidth={1.5} />
          <span className="ml-2 text-xs">等待生成结果</span>
        </div>
      )}
      {images.length > 1 ? (
        <p className="mt-1 text-xs text-muted-foreground">{images.length} 张图片</p>
      ) : null}
      <Button
        type="button"
        size="sm"
        variant="secondary"
        className="mt-2 w-full"
        disabled={cascadeRunning}
        data-testid={`canvas-output-cascade-${id}`}
        onClick={() => void runCascade(id)}
      >
        <GitBranch className="mr-1 size-3" />
        级联运行上游链
      </Button>
    </BaseNodeShell>
  );
}

import { Group } from "lucide-react";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { GroupNodeData } from "@infinite-canvas/canvas-schema";

export function GroupNode({ id, data, selected }: CanvasNodeProps<GroupNodeData>) {
  const items = Array.isArray(data.items) ? data.items : [];
  const w = Number(data.w) || 300;
  const h = Number(data.h) || 220;

  return (
    <BaseNodeShell
      type="group"
      title="分组"
      selected={selected}
      className="border-dashed"
      data-testid={`canvas-node-${id}`}
    >
      <div
        className="flex flex-col items-center justify-center rounded-md border border-dashed border-border bg-muted/30 text-muted-foreground"
        style={{ width: w - 48, height: h - 80, minHeight: 80 }}
      >
        <Group className="size-6" strokeWidth={1.5} />
        <span className="mt-1 text-xs">{items.length} 项</span>
      </div>
    </BaseNodeShell>
  );
}

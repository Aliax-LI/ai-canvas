import { useCallback, useMemo, useState } from "react";
import { GripVertical } from "lucide-react";
import { cn } from "@/lib/utils";
import { mediaPreviewUrl } from "../api";
import type { GeneratorSource } from "../lib/graph";

interface GeneratorInputListProps {
  nodeId: string;
  sources: GeneratorSource[];
  inputs: string[];
  onReorder: (movedId: string, targetId: string) => void;
  className?: string;
}

export function GeneratorInputList({
  nodeId,
  sources,
  inputs,
  onReorder,
  className,
}: GeneratorInputListProps) {
  const [dragId, setDragId] = useState<string | null>(null);

  const imageSources = useMemo(() => {
    const ordered = inputs
      .map((id) => sources.find((s) => s.id === id))
      .filter((s): s is GeneratorSource => Boolean(s));
    const rest = sources.filter((s) => !ordered.some((o) => o.id === s.id));
    return [...ordered, ...rest].filter((s) => s.refs?.length);
  }, [sources, inputs]);

  const handleDrop = useCallback(
    (targetId: string) => {
      if (dragId && dragId !== targetId) onReorder(dragId, targetId);
      setDragId(null);
    },
    [dragId, onReorder],
  );

  if (!imageSources.length) return null;

  return (
    <div className={cn("space-y-1", className)} data-testid={`canvas-input-list-${nodeId}`}>
      <p className="text-xs text-muted-foreground">参考图（拖拽排序）</p>
      {imageSources.map((src) => (
        <div
          key={src.id}
          draggable
          onDragStart={(e) => {
            setDragId(src.id);
            e.dataTransfer.setData("application/x-canvas-input", src.id);
            e.dataTransfer.effectAllowed = "move";
          }}
          onDragOver={(e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = "move";
          }}
          onDrop={(e) => {
            e.preventDefault();
            e.stopPropagation();
            const moved = e.dataTransfer.getData("application/x-canvas-input") || dragId;
            if (moved) handleDrop(src.id);
          }}
          className={cn(
            "flex items-center gap-1.5 rounded border border-border bg-muted/30 px-1.5 py-1 text-xs",
            dragId === src.id && "opacity-60",
          )}
          data-testid={`canvas-input-item-${src.id}`}
        >
          <GripVertical className="size-3 shrink-0 text-muted-foreground" />
          {src.preview ? (
            <img
              src={mediaPreviewUrl(src.preview, 48)}
              alt=""
              className="size-8 rounded object-cover"
            />
          ) : null}
          <span className="truncate">{src.label}</span>
        </div>
      ))}
    </div>
  );
}

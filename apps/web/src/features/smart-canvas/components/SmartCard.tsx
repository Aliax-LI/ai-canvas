import { useRef } from "react";
import { Group, ImageIcon, Repeat2, TextCursorInput, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { mediaPreviewUrl } from "../api";
import type { SmartNode } from "../types";

const TYPE_ICONS: Record<string, typeof ImageIcon> = {
  "smart-image": ImageIcon,
  "smart-prompt": TextCursorInput,
  "smart-group": Group,
  "smart-loop": Repeat2,
};

interface SmartCardProps {
  node: SmartNode;
  selected: boolean;
  scale: number;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onTextChange: (id: string, text: string) => void;
  onPointerDown: (id: string, e: React.PointerEvent) => void;
}

export function SmartCard({
  node,
  selected,
  scale,
  onSelect,
  onDelete,
  onTextChange,
  onPointerDown,
}: SmartCardProps) {
  const movedRef = useRef(false);
  const Icon = TYPE_ICONS[node.type] ?? ImageIcon;
  const width = node.w ?? (node.type === "smart-image" ? 240 : 316);

  const handleClick = () => {
    if (movedRef.current) {
      movedRef.current = false;
      return;
    }
    onSelect(node.id);
  };

  return (
    <article
      data-testid={`smart-card-${node.id}`}
      data-node-type={node.type}
      className={`absolute touch-none select-none rounded-xl border bg-card transition-shadow ${
        selected
          ? "border-[length:2px] border-canvas-node-selected shadow-md"
          : "border-border hover:shadow-md"
      }`}
      style={{
        left: node.x,
        top: node.y,
        width,
        transform: `scale(${node.type === "smart-image" ? (Number(node.scale) || 1) * scale : scale})`,
        transformOrigin: "top left",
      }}
      onPointerDown={(e) => {
        movedRef.current = false;
        onPointerDown(node.id, e);
      }}
      onPointerMove={() => {
        movedRef.current = true;
      }}
      onClick={handleClick}
    >
      <header className="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
        <div className="flex min-w-0 items-center gap-2">
          <Icon className="size-4 shrink-0 text-muted-foreground" strokeWidth={1.5} />
          <span className="truncate text-sm font-semibold">{node.title ?? node.type}</span>
        </div>
        {selected ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-7 shrink-0 text-destructive"
            aria-label="删除卡片"
            data-testid={`smart-card-delete-${node.id}`}
            onClick={(e) => {
              e.stopPropagation();
              onDelete(node.id);
            }}
          >
            <Trash2 className="size-3.5" />
          </Button>
        ) : null}
      </header>

      <div className="p-3">
        {node.type === "smart-image" ? <ImageCardBody node={node} /> : null}
        {node.type === "smart-prompt" ? (
          <Textarea
            value={String(node.text ?? "")}
            placeholder="输入提示词..."
            className="min-h-[120px] resize-none text-sm"
            onClick={(e) => e.stopPropagation()}
            onChange={(e) => onTextChange(node.id, e.target.value)}
          />
        ) : null}
        {node.type === "smart-group" ? (
          <p className="text-xs text-muted-foreground">
            分组内 {(node.items ?? []).length} 项 · 拖拽其他卡片到此处（待 parity）
          </p>
        ) : null}
        {node.type === "smart-loop" ? (
          <div className="space-y-1 text-sm">
            <div>轮数：{Number(node.count) || 1}</div>
            <div className="text-xs text-muted-foreground">模式：{String(node.mode ?? "serial")}</div>
          </div>
        ) : null}
      </div>
    </article>
  );
}

function ImageCardBody({ node }: { node: SmartNode }) {
  const images = node.images ?? [];
  if (!images.length) {
    return (
      <div className="flex aspect-video items-center justify-center rounded-lg border border-dashed text-xs text-muted-foreground">
        拖入或上传媒体
      </div>
    );
  }
  return (
    <div className="grid grid-cols-2 gap-2">
      {images.slice(0, 4).map((img, i) => (
        <img
          key={`${img.url ?? i}`}
          src={mediaPreviewUrl(img.url ?? "", 240)}
          alt={img.name ?? "media"}
          className="aspect-square rounded-lg border object-cover"
          draggable={false}
        />
      ))}
    </div>
  );
}

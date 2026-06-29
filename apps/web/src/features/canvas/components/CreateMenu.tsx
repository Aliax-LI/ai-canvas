import { useEffect, useRef } from "react";
import {
  BATCH1_NODE_TYPES,
  BATCH2_NODE_TYPES,
  CANVAS_NODE_REGISTRY,
  type RegisteredNodeType,
} from "@infinite-canvas/canvas-schema";
import {
  CircleDot,
  CloudLightning,
  Film,
  Group,
  ImagePlus,
  MessageSquareText,
  Repeat2,
  TextCursorInput,
  UploadCloud,
  Video,
  WandSparkles,
  Workflow,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const ICONS: Partial<Record<RegisteredNodeType, typeof ImagePlus>> = {
  image: UploadCloud,
  prompt: TextCursorInput,
  output: CircleDot,
  group: Group,
  generator: WandSparkles,
  msgen: CloudLightning,
  comfy: Workflow,
  rh: Workflow,
  video: Video,
  llm: MessageSquareText,
  loop: Repeat2,
  text: TextCursorInput,
  ltxDirector: Film,
  promptGroup: TextCursorInput,
};

interface CreateMenuProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (type: RegisteredNodeType) => void;
  onUpload: () => void;
}

function NodeGrid({
  types,
  onCreate,
  onUpload,
  onClose,
}: {
  types: readonly RegisteredNodeType[];
  onCreate: (type: RegisteredNodeType) => void;
  onUpload: () => void;
  onClose: () => void;
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {types.map((type) => {
        const def = CANVAS_NODE_REGISTRY[type];
        const Icon = ICONS[type] ?? ImagePlus;
        return (
          <button
            key={type}
            type="button"
            data-testid={`canvas-create-${type}`}
            className="flex items-start gap-3 rounded-lg border border-border p-3 text-left transition-colors hover:bg-accent hover:shadow-md"
            onClick={(e) => {
              e.stopPropagation();
              if (type === "image") onUpload();
              else onCreate(type);
              onClose();
            }}
          >
            <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted">
              <Icon className="size-4" strokeWidth={1.5} />
            </span>
            <span>
              <div className="text-sm font-semibold">{def.label}</div>
              <div className="mt-0.5 text-xs text-muted-foreground">{type}</div>
            </span>
          </button>
        );
      })}
    </div>
  );
}

export function CreateMenu({ open, onOpenChange, onCreate, onUpload }: CreateMenuProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onOpenChange(false);
      }
    };
    window.addEventListener("pointerdown", onPointerDown);
    return () => window.removeEventListener("pointerdown", onPointerDown);
  }, [open, onOpenChange]);

  if (!open) return null;

  return (
    <div
      ref={ref}
      data-testid="canvas-create-menu"
      className="absolute left-16 top-4 z-20 max-h-[calc(100%-2rem)] w-[min(420px,calc(100%-5rem))] overflow-y-auto rounded-xl border border-border bg-card p-3 shadow-lg"
    >
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        基础节点
      </div>
      <NodeGrid
        types={BATCH1_NODE_TYPES}
        onCreate={onCreate}
        onUpload={onUpload}
        onClose={() => onOpenChange(false)}
      />
      <div className="my-3 border-t border-border" />
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        生成 / 工作流
      </div>
      <NodeGrid
        types={BATCH2_NODE_TYPES}
        onCreate={onCreate}
        onUpload={onUpload}
        onClose={() => onOpenChange(false)}
      />
    </div>
  );
}

interface CreateFabProps {
  onClick: () => void;
}

export function CreateFab({ onClick }: CreateFabProps) {
  return (
    <Button
      type="button"
      size="icon"
      variant="secondary"
      className="absolute left-4 top-4 z-10 size-8 shadow-md"
      aria-label="添加节点"
      data-testid="canvas-create-fab"
      onClick={onClick}
    >
      <ImagePlus className="size-4" strokeWidth={1.5} />
    </Button>
  );
}

import { useEffect, useRef } from "react";
import {
  CANVAS_NODE_REGISTRY,
  type Batch1NodeType,
} from "@infinite-canvas/canvas-schema";
import {
  CircleDot,
  Group,
  ImagePlus,
  TextCursorInput,
  UploadCloud,
  WandSparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const ICONS: Record<Batch1NodeType, typeof ImagePlus> = {
  image: UploadCloud,
  prompt: TextCursorInput,
  output: CircleDot,
  group: Group,
  generator: WandSparkles,
};

interface CreateMenuProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (type: Batch1NodeType) => void;
  onUpload: () => void;
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

  const types = Object.keys(CANVAS_NODE_REGISTRY) as Batch1NodeType[];

  return (
    <div
      ref={ref}
      data-testid="canvas-create-menu"
      className="absolute left-16 top-4 z-20 w-[min(400px,calc(100%-5rem))] rounded-xl border border-border bg-card p-3 shadow-lg"
    >
      <div className="grid gap-2 sm:grid-cols-2">
        {types.map((type) => {
          const def = CANVAS_NODE_REGISTRY[type];
          const Icon = ICONS[type];
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
                onOpenChange(false);
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

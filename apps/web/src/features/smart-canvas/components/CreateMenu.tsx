import { useEffect, useRef } from "react";
import { Group, Plus, Repeat2, TextCursorInput, UploadCloud } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { SmartNodeType } from "../types";

export type CreateType = "image" | "group" | "prompt" | "loop";

const CREATE_OPTIONS: { type: CreateType; label: string; sub: string; icon: typeof UploadCloud }[] = [
  { type: "image", label: "上传", sub: "图片、音频、视频都能导入", icon: UploadCloud },
  { type: "group", label: "分组", sub: "把提示词、图片、循环收进同一组", icon: Group },
  { type: "prompt", label: "提示词", sub: "手写或用 LLM 生成文本", icon: TextCursorInput },
  { type: "loop", label: "循环", sub: "控制运行轮数、批次和变量", icon: Repeat2 },
];

const TYPE_MAP: Record<CreateType, SmartNodeType> = {
  image: "smart-image",
  group: "smart-group",
  prompt: "smart-prompt",
  loop: "smart-loop",
};

interface CreateMenuProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (type: SmartNodeType) => void;
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

  return (
    <div
      ref={ref}
      data-testid="smart-create-menu"
      className="absolute left-1/2 top-1/2 z-20 w-[min(520px,calc(100%-2rem))] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-border bg-card p-4 shadow-lg"
    >
      <div className="grid gap-2 sm:grid-cols-2">
        {CREATE_OPTIONS.map((opt) => {
          const Icon = opt.icon;
          return (
            <button
              key={opt.type}
              type="button"
              data-testid={`smart-create-${opt.type}`}
              className="flex items-start gap-3 rounded-xl border border-border p-3 text-left transition-colors hover:bg-accent hover:shadow-md"
              onClick={(e) => {
                e.stopPropagation();
                if (opt.type === "image") onUpload();
                else onCreate(TYPE_MAP[opt.type]);
                onOpenChange(false);
              }}
            >
              <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-muted">
                <Icon className="size-5" strokeWidth={1.5} />
              </span>
              <span>
                <div className="text-sm font-semibold">{opt.label}</div>
                <div className="mt-0.5 text-xs text-muted-foreground">{opt.sub}</div>
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
      className="absolute bottom-6 right-6 z-10 size-12 rounded-full shadow-md"
      aria-label="添加卡片"
      data-testid="smart-create-fab"
      onClick={onClick}
    >
      <Plus className="size-5" strokeWidth={1.5} />
    </Button>
  );
}
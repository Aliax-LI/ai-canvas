import { useMemo, useState } from "react";
import { Link, Outlet, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CanvasShellProvider } from "@/features/canvas/context";
import type { SaveState } from "@/features/canvas/types";

function saveLabel(state: SaveState): string {
  switch (state) {
    case "saving":
      return "保存中…";
    case "pending":
      return "待保存";
    case "saved":
      return "已保存";
    case "error":
      return "保存失败";
    default:
      return "未修改";
  }
}

export function CanvasShell() {
  const { id } = useParams<{ id: string }>();
  const [title, setTitle] = useState("画布");
  const [saveState, setSaveState] = useState<SaveState>("idle");

  const shellValue = useMemo(
    () => ({ title, saveState, setTitle, setSaveState }),
    [title, saveState],
  );

  return (
    <CanvasShellProvider value={shellValue}>
      <div data-testid="canvas-shell" className="flex h-full min-h-0 flex-col bg-canvas-bg">
        <header className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-card/80 px-4 backdrop-blur">
          <div className="flex min-w-0 items-center gap-2">
            <Button variant="ghost" size="icon" className="size-8" asChild>
              <Link to="/canvases" aria-label="返回画布列表">
                <ArrowLeft className="size-[18px]" strokeWidth={1.5} />
              </Link>
            </Button>
            <Input
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                setSaveState("pending");
              }}
              className="h-8 max-w-[240px] border-none bg-transparent px-1 text-sm font-medium shadow-none focus-visible:ring-0"
              aria-label="画布标题"
              data-testid="canvas-title-input"
            />
            <span className="hidden font-mono text-xs text-muted-foreground sm:inline">{id}</span>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`text-xs ${
                saveState === "error" ? "text-destructive" : "text-muted-foreground"
              }`}
              data-testid="canvas-save-status"
            >
              <span
                className={`mr-1.5 inline-block size-2 rounded-full ${
                  saveState === "saved"
                    ? "bg-success"
                    : saveState === "saving" || saveState === "pending"
                      ? "bg-warning"
                      : "bg-muted-foreground/40"
                }`}
              />
              {saveLabel(saveState)}
            </span>
          </div>
        </header>

        <main className="relative flex flex-1 min-h-0 flex-col">
          <Outlet />
        </main>
      </div>
    </CanvasShellProvider>
  );
}

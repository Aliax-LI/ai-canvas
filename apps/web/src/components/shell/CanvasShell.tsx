import { Link, Outlet, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export function CanvasShell() {
  const { id } = useParams<{ id: string }>();

  return (
    <div data-testid="canvas-shell" className="flex h-full min-h-0 flex-col bg-canvas-bg">
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-card/80 px-4 backdrop-blur">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="size-8" asChild>
            <Link to="/canvases" aria-label="返回画布列表">
              <ArrowLeft className="size-[18px]" strokeWidth={1.5} />
            </Link>
          </Button>
          <span className="text-sm font-medium">画布 {id ?? "—"}</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="size-2 rounded-full bg-muted-foreground/40" />
          未保存
        </div>
      </header>

      <div className="relative flex flex-1 min-h-0">
        <aside className="absolute left-4 top-4 z-10 flex flex-col gap-1 rounded-md border border-border bg-card p-1 shadow-md">
          <Button variant="ghost" size="icon" className="size-8" aria-label="快捷工具（占位）">
            <span className="text-xs">+</span>
          </Button>
        </aside>

        <main className="flex flex-1 items-center justify-center">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

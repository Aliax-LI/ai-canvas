import { ScrollText } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import type { CanvasLogEntry } from "../lib/runHelpers";

function formatTime(ts: number): string {
  try {
    return new Date(ts).toLocaleTimeString("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "";
  }
}

function statusLabel(status: CanvasLogEntry["status"]): string {
  switch (status) {
    case "running":
      return "运行中";
    case "succeeded":
      return "成功";
    case "failed":
      return "失败";
    default:
      return status;
  }
}

interface LogsPanelProps {
  logs: CanvasLogEntry[];
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function LogsPanel({ logs, open, onOpenChange }: LogsPanelProps) {
  const sorted = [...logs].sort((a, b) => b.ts - a.ts);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetTrigger asChild>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="absolute right-4 top-4 z-10 gap-1.5 bg-card/90 shadow-sm backdrop-blur"
          data-testid="canvas-logs-toggle"
        >
          <ScrollText className="size-4" />
          日志
          {logs.length > 0 ? (
            <span className="rounded-full bg-muted px-1.5 text-xs">{logs.length}</span>
          ) : null}
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-full sm:max-w-md" data-testid="canvas-logs-panel">
        <SheetHeader>
          <SheetTitle>生成日志</SheetTitle>
          <p className="text-sm text-muted-foreground">节点运行记录（最近 {logs.length} 条）</p>
        </SheetHeader>
        <div className="mt-4 flex flex-col gap-2 overflow-y-auto pr-1" style={{ maxHeight: "calc(100vh - 8rem)" }}>
          {sorted.length === 0 ? (
            <p className="text-sm text-muted-foreground">暂无运行记录</p>
          ) : (
            sorted.map((entry) => (
              <div
                key={entry.id}
                className="rounded-md border border-border bg-muted/30 px-3 py-2 text-sm"
                data-testid={`canvas-log-entry-${entry.id}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs text-muted-foreground">{formatTime(entry.ts)}</span>
                  <span
                    className={
                      entry.status === "failed"
                        ? "text-xs text-destructive"
                        : entry.status === "succeeded"
                          ? "text-xs text-success"
                          : "text-xs text-info"
                    }
                  >
                    {statusLabel(entry.status)}
                  </span>
                </div>
                <p className="mt-1 truncate text-xs text-muted-foreground">
                  {entry.nodeType ?? "node"} · {entry.nodeId}
                </p>
                {entry.message ? <p className="mt-1 text-xs">{entry.message}</p> : null}
              </div>
            ))
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

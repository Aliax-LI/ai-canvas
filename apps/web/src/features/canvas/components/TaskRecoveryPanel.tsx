import { useMemo } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import type { Node } from "@xyflow/react";
import type { CanvasLogEntry } from "../lib/runHelpers";

interface TaskRecoveryPanelProps {
  nodes: Node[];
  logs: CanvasLogEntry[];
  onClearStatus: (nodeIds: string[]) => void;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

function nodeType(node: Node): string {
  return String(node.data?.nodeType ?? node.type ?? "");
}

export function TaskRecoveryPanel({
  nodes,
  logs,
  onClearStatus,
  open,
  onOpenChange,
}: TaskRecoveryPanelProps) {
  const stuckNodes = useMemo(() => {
    const fromNodes = nodes.filter((n) => {
      const data = (n.data ?? {}) as Record<string, unknown>;
      const status = String(data.runStatus ?? "");
      return status === "running" || status === "queued" || Boolean(data.running);
    });
    const failedLogNodeIds = new Set(
      logs.filter((l) => l.status === "failed").map((l) => l.nodeId).filter(Boolean),
    );
    const fromLogs = nodes.filter(
      (n) => failedLogNodeIds.has(n.id) && !fromNodes.some((x) => x.id === n.id),
    );
    return [...fromNodes, ...fromLogs];
  }, [nodes, logs]);

  const handleClear = () => {
    onClearStatus(stuckNodes.map((n) => n.id));
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetTrigger asChild>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-8 gap-1.5"
          data-testid="canvas-task-recovery"
        >
          <AlertTriangle className="size-3.5" />
          任务恢复
          {stuckNodes.length > 0 ? (
            <span className="rounded-full bg-destructive/15 px-1.5 text-xs text-destructive">
              {stuckNodes.length}
            </span>
          ) : null}
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-full sm:max-w-sm">
        <SheetHeader>
          <SheetTitle>任务恢复</SheetTitle>
          <p className="text-sm text-muted-foreground">
            显示运行中或失败的任务节点，可一键清除状态
          </p>
        </SheetHeader>
        <div className="mt-4 space-y-2">
          {stuckNodes.length === 0 ? (
            <p className="text-sm text-muted-foreground">没有需要恢复的任务</p>
          ) : (
            stuckNodes.map((n) => {
              const data = (n.data ?? {}) as Record<string, unknown>;
              const status = String(data.runStatus ?? (data.running ? "running" : ""));
              const err = String(data.runError ?? "");
              return (
                <div
                  key={n.id}
                  className="rounded-md border border-border bg-muted/30 px-3 py-2 text-sm"
                  data-testid={`canvas-recovery-item-${n.id}`}
                >
                  <p className="font-medium">{nodeType(n)} · {n.id}</p>
                  <p className="text-xs text-muted-foreground">状态: {status || "unknown"}</p>
                  {err ? <p className="mt-1 text-xs text-destructive">{err}</p> : null}
                </div>
              );
            })
          )}
        </div>
        {stuckNodes.length > 0 ? (
          <Button type="button" className="mt-4 w-full" variant="secondary" onClick={handleClear}>
            <RotateCcw className="mr-1 size-4" />
            清除状态
          </Button>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}

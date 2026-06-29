import { useCallback, useRef, useState } from "react";
import { Download, Upload } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import type { Edge, Node, Viewport } from "@xyflow/react";
import {
  flowEdgesToLegacy,
  flowNodesToLegacy,
  flowViewportToLegacy,
  legacyConnectionsToFlow,
  legacyNodesToFlow,
  newConnectionId,
  newNodeId,
} from "../lib/serialize";

export interface WorkflowPayload {
  format: "infinite-canvas-workflow";
  version: 1;
  exported_at: number;
  nodes: ReturnType<typeof flowNodesToLegacy>;
  connections: ReturnType<typeof flowEdgesToLegacy>;
  viewport?: ReturnType<typeof flowViewportToLegacy>;
}

interface PendingImport {
  payload: WorkflowPayload;
  mode: "merge" | "replace";
}

interface WorkflowMenuProps {
  title: string;
  nodes: Node[];
  edges: Edge[];
  viewport: Viewport;
  onImport: (nodes: Node[], edges: Edge[], mode: "merge" | "replace") => void;
}

function workflowFilename(title: string): string {
  const safe = (title || "canvas-workflow").replace(/[\\/:*?"<>|]+/g, "_").slice(0, 48);
  const stamp = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15);
  return `${safe || "canvas-workflow"}-${stamp}.json`;
}

function normalizeImportedWorkflow(data: unknown): WorkflowPayload | null {
  if (!data || typeof data !== "object") return null;
  const obj = data as Record<string, unknown>;
  const nodes = Array.isArray(obj.nodes)
    ? obj.nodes
    : Array.isArray((obj.workflow as Record<string, unknown> | undefined)?.nodes)
      ? ((obj.workflow as Record<string, unknown>).nodes as unknown[])
      : [];
  const connections = Array.isArray(obj.connections)
    ? obj.connections
    : Array.isArray((obj.workflow as Record<string, unknown> | undefined)?.connections)
      ? ((obj.workflow as Record<string, unknown>).connections as unknown[])
      : [];
  if (!nodes.length) return null;
  return {
    format: "infinite-canvas-workflow",
    version: 1,
    exported_at: Date.now(),
    nodes: nodes as WorkflowPayload["nodes"],
    connections: connections as WorkflowPayload["connections"],
    viewport: obj.viewport as WorkflowPayload["viewport"],
  };
}

export function WorkflowMenu({ title, nodes, edges, viewport, onImport }: WorkflowMenuProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [pending, setPending] = useState<PendingImport | null>(null);

  const handleExport = useCallback(() => {
    const payload: WorkflowPayload = {
      format: "infinite-canvas-workflow",
      version: 1,
      exported_at: Date.now(),
      nodes: flowNodesToLegacy(nodes),
      connections: flowEdgesToLegacy(edges),
      viewport: flowViewportToLegacy(viewport),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = workflowFilename(title);
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1200);
    toast.success("已导出工作流 JSON");
  }, [title, nodes, edges, viewport]);

  const handleFile = useCallback(async (file: File) => {
    try {
      const text = await file.text();
      const data = JSON.parse(text) as unknown;
      const payload = normalizeImportedWorkflow(data);
      if (!payload) {
        toast.error("工作流 JSON 无效或没有节点");
        return;
      }
      setPending({ payload, mode: "merge" });
    } catch {
      toast.error("无法解析 JSON 文件");
    }
  }, []);

  const applyImport = useCallback(() => {
    if (!pending) return;
    const { payload, mode } = pending;
    const srcNodes = payload.nodes.filter(Boolean);
    const srcConnections = payload.connections.filter(Boolean);
    if (!srcNodes.length) {
      toast.error("工作流中没有可导入的节点");
      return;
    }

    if (mode === "replace") {
      const flowNodes = legacyNodesToFlow(srcNodes);
      const flowEdges = legacyConnectionsToFlow(srcConnections);
      onImport(flowNodes, flowEdges, "replace");
      toast.success(`已替换为 ${flowNodes.length} 个节点`);
      setPending(null);
      return;
    }

    const minX = Math.min(...srcNodes.map((n) => Number(n.x) || 0));
    const minY = Math.min(...srcNodes.map((n) => Number(n.y) || 0));
    const offsetX = 80 - minX;
    const offsetY = 80 - minY;
    const idMap = new Map<string, string>();

    const remapped = srcNodes.map((n) => {
      const copy = { ...n, running: false };
      const oldId = copy.id;
      copy.id = newNodeId(String(copy.type ?? "n").slice(0, 3));
      copy.x = Number(copy.x || 0) + offsetX;
      copy.y = Number(copy.y || 0) + offsetY;
      idMap.set(oldId, copy.id);
      return copy;
    });

    remapped.forEach((node) => {
      const legacy = node as Record<string, unknown>;
      if ((node.type === "group" || node.type === "promptGroup") && Array.isArray(legacy.items)) {
        legacy.items = (legacy.items as string[])
          .map((itemId) => idMap.get(itemId) || itemId)
          .filter((itemId) => idMap.has(itemId));
      }
    });

    const newConnections = srcConnections
      .map((c) => ({
        ...c,
        id: newConnectionId(),
        from: idMap.get(c.from) ?? c.from,
        to: idMap.get(c.to) ?? c.to,
      }))
      .filter((c) => c.from && c.to);

    const importedNodes = legacyNodesToFlow(remapped);
    const importedEdges = legacyConnectionsToFlow(newConnections);
    onImport(importedNodes, importedEdges, "merge");
    toast.success(`已导入 ${importedNodes.length} 个节点`);
    setPending(null);
  }, [pending, onImport]);

  return (
    <>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="h-8"
        data-testid="canvas-workflow-export"
        onClick={handleExport}
      >
        <Download className="mr-1 size-3.5" />
        导出
      </Button>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="h-8"
        data-testid="canvas-workflow-import"
        onClick={() => fileRef.current?.click()}
      >
        <Upload className="mr-1 size-3.5" />
        导入
      </Button>
      <input
        ref={fileRef}
        type="file"
        accept="application/json,.json"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void handleFile(file);
          e.target.value = "";
        }}
      />

      <Dialog open={Boolean(pending)} onOpenChange={(open) => !open && setPending(null)}>
        <DialogContent>
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold">导入工作流</h2>
              <p className="text-sm text-muted-foreground">
                检测到 {pending?.payload.nodes.length ?? 0} 个节点、
                {pending?.payload.connections.length ?? 0} 条连线。选择导入方式：
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                type="button"
                variant={pending?.mode === "merge" ? "default" : "outline"}
                size="sm"
                onClick={() => setPending((p) => (p ? { ...p, mode: "merge" } : p))}
              >
                合并追加
              </Button>
              <Button
                type="button"
                variant={pending?.mode === "replace" ? "default" : "outline"}
                size="sm"
                onClick={() => setPending((p) => (p ? { ...p, mode: "replace" } : p))}
              >
                替换全部
              </Button>
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setPending(null)}>
                取消
              </Button>
              <Button type="button" onClick={applyImport}>
                确认导入
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

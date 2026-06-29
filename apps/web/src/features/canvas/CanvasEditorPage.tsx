import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Connection, Edge, Node, Viewport } from "@xyflow/react";
import { GitBranch, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import type { RegisteredNodeType } from "@infinite-canvas/canvas-schema";
import {
  createCanvasNode,
  fetchCanvasEditor,
  newCanvasClientId,
  saveCanvasEditor,
  uploadCanvasMedia,
} from "./api";
import { AssetsSidebar, AssetsToggle } from "./components/AssetsSidebar";
import { CanvasFlow } from "./components/CanvasFlow";
import { CreateFab, CreateMenu } from "./components/CreateMenu";
import { CanvasEditorActionsProvider } from "./components/EditorActionsContext";
import { LogsPanel } from "./components/LogsPanel";
import { useCanvasShell } from "./context";
import { runNodeCascade, resolveCascadeTargetId } from "./lib/cascade";
import {
  isGeneratorType,
  resolveRunPayload,
  syncGeneratorInputs,
  type LoopContext,
} from "./lib/graph";
import {
  cloneNodesForPaste,
  cloneSnapshot,
  type ClipboardPayload,
  UNDO_MAX,
} from "./lib/history";
import {
  mergeOutputImages,
  newLogEntry,
  type CanvasLogEntry,
} from "./lib/runHelpers";
import {
  flowEdgesToLegacy,
  flowNodesToLegacy,
  flowViewportToLegacy,
  legacyConnectionsToFlow,
  legacyNodesToFlow,
  legacyViewportToFlow,
  newConnectionId,
  newNodeId,
} from "./lib/serialize";

const CLIENT_ID = newCanvasClientId();
const SAVE_DELAY_MS = 450;
const MAX_LOGS = 500;

function normalizeLogs(raw: Record<string, unknown>[]): CanvasLogEntry[] {
  return raw.map((item, i) => ({
    id: String(item.id ?? `log_legacy_${i}`),
    ts: Number(item.ts ?? item.time ?? Date.now()),
    nodeId: String(item.nodeId ?? item.node_id ?? ""),
    nodeType: item.nodeType ? String(item.nodeType) : undefined,
    status: (item.status as CanvasLogEntry["status"]) ?? "succeeded",
    message: item.message ? String(item.message) : undefined,
  }));
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || target.isContentEditable;
}

export function CanvasEditorPage() {
  const { id = "" } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const { title, setTitle, setSaveState } = useCanvasShell();
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hydratedRef = useRef(false);
  const titleSaveSkip = useRef(true);
  const lastAddAtRef = useRef(0);
  const nodesRef = useRef<Node[]>([]);
  const edgesRef = useRef<Edge[]>([]);
  const undoStackRef = useRef<ReturnType<typeof cloneSnapshot>[]>([]);
  const redoStackRef = useRef<ReturnType<typeof cloneSnapshot>[]>([]);
  const clipboardRef = useRef<ClipboardPayload | null>(null);
  const cascadeRunningRef = useRef(false);

  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [viewport, setViewport] = useState<Viewport>({ x: 0, y: 0, zoom: 1 });
  const [icon, setIcon] = useState("layout");
  const [settings, setSettings] = useState<Record<string, unknown>>({});
  const [logs, setLogs] = useState<CanvasLogEntry[]>([]);
  const [logsOpen, setLogsOpen] = useState(false);
  const [assetsOpen, setAssetsOpen] = useState(false);
  const [cascadeRunning, setCascadeRunning] = useState(false);
  const [updatedAt, setUpdatedAt] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [flowViewport, setFlowViewport] = useState<Viewport | undefined>();
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    nodesRef.current = nodes;
  }, [nodes]);

  useEffect(() => {
    edgesRef.current = edges;
  }, [edges]);

  const canvasQuery = useQuery({
    queryKey: ["canvas-editor", id],
    queryFn: () => fetchCanvasEditor(id),
    enabled: Boolean(id),
  });

  useEffect(() => {
    if (!canvasQuery.data || hydratedRef.current) return;
    const canvas = canvasQuery.data;
    setNodes(legacyNodesToFlow(canvas.nodes));
    setEdges(legacyConnectionsToFlow(canvas.connections));
    const vp = legacyViewportToFlow(canvas.viewport);
    setViewport(vp);
    setFlowViewport(vp);
    setTitle(canvas.title || "未命名画布");
    setIcon(canvas.icon || "layout");
    setSettings(canvas.settings ?? {});
    setLogs(normalizeLogs(canvas.logs));
    setUpdatedAt(canvas.updated_at ?? 0);
    undoStackRef.current = [];
    redoStackRef.current = [];
    hydratedRef.current = true;
  }, [canvasQuery.data, setTitle]);

  useEffect(() => {
    hydratedRef.current = false;
    setSaveState("idle");
    titleSaveSkip.current = true;
  }, [id, setSaveState]);

  const saveMutation = useMutation({
    mutationFn: (payload: Parameters<typeof saveCanvasEditor>[1]) => saveCanvasEditor(id, payload),
    onMutate: () => setSaveState("saving"),
    onSuccess: (canvas) => {
      setUpdatedAt(canvas.updated_at ?? 0);
      setSaveState("saved");
      void queryClient.invalidateQueries({ queryKey: ["canvases"] });
    },
    onError: (e) => {
      setSaveState("error");
      toast.error(e instanceof Error ? e.message : "保存失败");
    },
  });

  const flushSave = useCallback(() => {
    if (!id || !hydratedRef.current) return;
    saveMutation.mutate({
      title,
      icon,
      nodes: flowNodesToLegacy(nodesRef.current),
      connections: flowEdgesToLegacy(edgesRef.current),
      viewport: flowViewportToLegacy(viewport),
      logs: logs.slice(-MAX_LOGS) as unknown as Record<string, unknown>[],
      settings,
      base_updated_at: updatedAt,
      client_id: CLIENT_ID,
    });
  }, [id, title, icon, viewport, logs, settings, updatedAt, saveMutation]);

  const scheduleSave = useCallback(() => {
    setSaveState("pending");
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => {
      flushSave();
    }, SAVE_DELAY_MS);
  }, [flushSave, setSaveState]);

  useEffect(
    () => () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    },
    [],
  );

  useEffect(() => {
    if (titleSaveSkip.current) {
      titleSaveSkip.current = false;
      return;
    }
    if (hydratedRef.current) scheduleSave();
  }, [title, scheduleSave]);

  const pushUndo = useCallback(() => {
    undoStackRef.current.push(cloneSnapshot(nodesRef.current, edgesRef.current));
    if (undoStackRef.current.length > UNDO_MAX) undoStackRef.current.shift();
    redoStackRef.current = [];
  }, []);

  const undo = useCallback(() => {
    if (!undoStackRef.current.length) return;
    redoStackRef.current.push(cloneSnapshot(nodesRef.current, edgesRef.current));
    const state = undoStackRef.current.pop()!;
    setNodes(state.nodes);
    setEdges(state.edges);
    scheduleSave();
  }, [scheduleSave]);

  const redo = useCallback(() => {
    if (!redoStackRef.current.length) return;
    undoStackRef.current.push(cloneSnapshot(nodesRef.current, edgesRef.current));
    const state = redoStackRef.current.pop()!;
    setNodes(state.nodes);
    setEdges(state.edges);
    scheduleSave();
  }, [scheduleSave]);

  const screenToFlowPosition = useCallback((offset = 0) => {
    const cx = (-viewport.x + window.innerWidth / 2) / viewport.zoom;
    const cy = (-viewport.y + window.innerHeight / 2) / viewport.zoom;
    return { x: cx + offset, y: cy + offset };
  }, [viewport]);

  const addNode = useCallback(
    (type: RegisteredNodeType, extra?: Record<string, unknown>) => {
      const now = Date.now();
      if (now - lastAddAtRef.current < 200) return null;
      lastAddAtRef.current = now;
      pushUndo();
      const offset = nodesRef.current.length * 24;
      const pos = screenToFlowPosition(offset);
      const legacy = createCanvasNode(type, pos.x, pos.y);
      const flowNodes = legacyNodesToFlow([{ ...legacy, ...extra }]);
      const newNode = flowNodes[0];
      setNodes((prev) => [...prev, newNode]);
      scheduleSave();
      return newNode;
    },
    [screenToFlowPosition, scheduleSave, pushUndo],
  );

  const updateNodeData = useCallback(
    (nodeId: string, patch: Record<string, unknown>) => {
      setNodes((prev) => {
        const next = prev.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, ...patch } } : n,
        );
        nodesRef.current = next;
        return next;
      });
      if (!cascadeRunningRef.current) scheduleSave();
    },
    [scheduleSave],
  );

  const appendLog = useCallback(
    (entry: Omit<CanvasLogEntry, "id" | "ts"> & { ts?: number }) => {
      setLogs((prev) => [...prev.slice(-(MAX_LOGS - 1)), newLogEntry(entry)]);
      scheduleSave();
    },
    [scheduleSave],
  );

  const writeOutputImages = useCallback(
    (outputNodeId: string, urls: string[]) => {
      if (!urls.length) return;
      setNodes((prev) =>
        prev.map((n) => {
          if (n.id !== outputNodeId) return n;
          const images = mergeOutputImages(
            (n.data as { images?: { url?: string }[] }).images,
            urls,
          );
          return { ...n, data: { ...n.data, images } };
        }),
      );
      scheduleSave();
    },
    [scheduleSave],
  );

  const getRunContext = useCallback(
    (nodeId: string, loopCtx?: LoopContext) =>
      resolveRunPayload(nodeId, nodesRef.current, edgesRef.current, loopCtx),
    [],
  );

  const runCascade = useCallback(
    async (nodeId: string) => {
      if (cascadeRunningRef.current) {
        toast.info("级联运行进行中");
        return;
      }
      const targetId = resolveCascadeTargetId(nodeId, nodesRef.current, edgesRef.current);
      if (!targetId) {
        toast.error("没有可级联运行的节点链");
        return;
      }

      cascadeRunningRef.current = true;
      setCascadeRunning(true);
      appendLog({
        nodeId: targetId,
        status: "running",
        message: "开始级联运行",
      });

      try {
        await runNodeCascade(targetId, {
          nodes: nodesRef.current,
          edges: edgesRef.current,
          getNodes: () => nodesRef.current,
          getEdges: () => edgesRef.current,
          updateNodeData,
          appendLog,
          writeOutputImages,
        });
        appendLog({ nodeId: targetId, status: "succeeded", message: "级联运行完成" });
        toast.success("级联运行完成");
        scheduleSave();
      } catch (e) {
        const msg = e instanceof Error ? e.message : "级联运行失败";
        appendLog({ nodeId: targetId, status: "failed", message: msg });
        toast.error(msg);
        scheduleSave();
      } finally {
        cascadeRunningRef.current = false;
        setCascadeRunning(false);
      }
    },
    [updateNodeData, appendLog, writeOutputImages, scheduleSave],
  );

  const copySelected = useCallback(() => {
    const selected = nodesRef.current.filter((n) => n.selected);
    if (!selected.length) return;
    const ids = new Set(selected.map((n) => n.id));
    clipboardRef.current = {
      nodes: structuredClone(selected),
      edges: edgesRef.current.filter((e) => ids.has(e.source) && ids.has(e.target)),
    };
    toast.success(`已复制 ${selected.length} 个节点`);
  }, []);

  const paste = useCallback(() => {
    const clip = clipboardRef.current;
    if (!clip?.nodes.length) return;
    pushUndo();
    const center = screenToFlowPosition(0);
    const { nodes: pastedNodes, edges: pastedEdges } = cloneNodesForPaste(
      clip,
      center,
      newNodeId,
      newConnectionId,
    );
    setNodes((prev) => [...prev.map((n) => ({ ...n, selected: false })), ...pastedNodes]);
    setEdges((prev) => [...prev, ...pastedEdges]);
    scheduleSave();
    toast.success(`已粘贴 ${pastedNodes.length} 个节点`);
  }, [pushUndo, screenToFlowPosition, scheduleSave]);

  const handleConnect = useCallback(
    (connection: Connection) => {
      if (!connection.source || !connection.target) return;
      pushUndo();
      const newEdge: Edge = {
        id: newConnectionId(),
        source: connection.source,
        target: connection.target,
        sourceHandle: connection.sourceHandle,
        targetHandle: connection.targetHandle,
        type: "default",
      };

      const nextEdges = [...edgesRef.current, newEdge];
      setEdges(nextEdges);

      const targetNode = nodesRef.current.find((n) => n.id === connection.target);
      if (targetNode && isGeneratorType(targetNode.type)) {
        const inputs = syncGeneratorInputs(
          connection.target,
          (targetNode.data ?? {}) as Record<string, unknown>,
          nodesRef.current,
          nextEdges,
        );
        updateNodeData(connection.target, { inputs });
      } else {
        scheduleSave();
      }
    },
    [pushUndo, updateNodeData, scheduleSave],
  );

  const handleNodesChange = useCallback(
    (nextNodes: Node[]) => {
      const removed = nodesRef.current.filter(
        (n) => !nextNodes.some((x) => x.id === n.id),
      );
      if (removed.length) pushUndo();
      setNodes(nextNodes);
      if (removed.length) scheduleSave();
    },
    [pushUndo, scheduleSave],
  );

  const handleAssetClick = useCallback(
    (item: { url: string; name: string }) => {
      const selectedGen = nodesRef.current.find(
        (n) => n.selected && isGeneratorType(n.type),
      );
      const newNode = addNode("image", { url: item.url, name: item.name });
      if (newNode && selectedGen) {
        const edge: Edge = {
          id: newConnectionId(),
          source: newNode.id,
          target: selectedGen.id,
          type: "default",
        };
        setEdges((prev) => [...prev, edge]);
        const inputs = syncGeneratorInputs(
          selectedGen.id,
          (selectedGen.data ?? {}) as Record<string, unknown>,
          [...nodesRef.current, newNode],
          [...edgesRef.current, edge],
        );
        updateNodeData(selectedGen.id, { inputs });
      }
    },
    [addNode, updateNodeData],
  );

  const runSelectedCascade = useCallback(() => {
    const selected = nodesRef.current.filter((n) => n.selected);
    const target =
      selected.find((n) => resolveCascadeTargetId(n.id, nodesRef.current, edgesRef.current)) ??
      selected[0];
    if (!target) {
      toast.error("请先选中可运行的节点");
      return;
    }
    void runCascade(target.id);
  }, [runCascade]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (isEditableTarget(e.target)) return;
      const mod = e.metaKey || e.ctrlKey;
      if (!mod) return;
      if (e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        undo();
      } else if ((e.key === "z" && e.shiftKey) || e.key === "y") {
        e.preventDefault();
        redo();
      } else if (e.key === "c") {
        e.preventDefault();
        copySelected();
      } else if (e.key === "v") {
        e.preventDefault();
        paste();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [undo, redo, copySelected, paste]);

  const editorActions = useMemo(
    () => ({
      nodes,
      edges,
      updateNodeData,
      scheduleSave,
      pushUndo,
      getRunContext,
      appendLog,
      writeOutputImages,
      runCascade,
      undo,
      redo,
      copySelected,
      paste,
      cascadeRunning,
    }),
    [
      nodes,
      edges,
      updateNodeData,
      scheduleSave,
      pushUndo,
      getRunContext,
      appendLog,
      writeOutputImages,
      runCascade,
      undo,
      redo,
      copySelected,
      paste,
      cascadeRunning,
    ],
  );

  const uploadMutation = useMutation({
    mutationFn: uploadCanvasMedia,
    onSuccess: (files) => {
      for (const file of files) {
        addNode("image", { url: file.url, name: file.name });
      }
      toast.success("已上传");
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "上传失败"),
  });

  if (canvasQuery.isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 size-5 animate-spin" />
        加载画布…
      </div>
    );
  }

  if (canvasQuery.isError) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3">
        <p className="text-sm text-destructive">无法加载画布</p>
        <Button variant="outline" asChild>
          <Link to="/canvases">返回列表</Link>
        </Button>
      </div>
    );
  }

  return (
    <div data-testid="canvas-editor-page" className="relative flex flex-1 min-h-0 flex-col">
      <CanvasEditorActionsProvider value={editorActions}>
        <div className="flex h-9 shrink-0 items-center gap-2 border-b border-border bg-card/60 px-3">
          <AssetsToggle open={assetsOpen} onToggle={() => setAssetsOpen((v) => !v)} />
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-8"
            disabled={cascadeRunning}
            data-testid="canvas-cascade-run"
            onClick={runSelectedCascade}
          >
            {cascadeRunning ? (
              <Loader2 className="mr-1 size-3.5 animate-spin" />
            ) : (
              <GitBranch className="mr-1 size-3.5" />
            )}
            运行选中链
          </Button>
        </div>

        <LogsPanel logs={logs} open={logsOpen} onOpenChange={setLogsOpen} />
        <div className="flex flex-1 min-h-0">
          <CanvasFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={setEdges}
            onViewportChange={setViewport}
            initialViewport={flowViewport}
            onDirty={scheduleSave}
            onConnect={handleConnect}
          />
          <AssetsSidebar
            open={assetsOpen}
            onOpenChange={setAssetsOpen}
            onAddImageNode={(url, name) => handleAssetClick({ url, name })}
          />
        </div>
      </CanvasEditorActionsProvider>

      <CreateMenu
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreate={(type) => addNode(type)}
        onUpload={() => fileRef.current?.click()}
      />
      <CreateFab onClick={() => setCreateOpen(true)} />

      <input
        ref={fileRef}
        type="file"
        accept="image/*,video/*,audio/*"
        multiple
        className="hidden"
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          if (files.length) uploadMutation.mutate(files);
          e.target.value = "";
        }}
      />
    </div>
  );
}

import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Edge, Node, Viewport } from "@xyflow/react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import type { Batch1NodeType } from "@infinite-canvas/canvas-schema";
import {
  createCanvasNode,
  fetchCanvasEditor,
  newCanvasClientId,
  saveCanvasEditor,
  uploadCanvasMedia,
} from "./api";
import { CanvasFlow } from "./components/CanvasFlow";
import { CreateFab, CreateMenu } from "./components/CreateMenu";
import { CanvasEditorActionsProvider } from "./components/EditorActionsContext";
import { useCanvasShell } from "./context";
import {
  flowEdgesToLegacy,
  flowNodesToLegacy,
  flowViewportToLegacy,
  legacyConnectionsToFlow,
  legacyNodesToFlow,
  legacyViewportToFlow,
} from "./lib/serialize";

const CLIENT_ID = newCanvasClientId();
const SAVE_DELAY_MS = 450;

export function CanvasEditorPage() {
  const { id = "" } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const { title, setTitle, setSaveState } = useCanvasShell();
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hydratedRef = useRef(false);
  const titleSaveSkip = useRef(true);
  const lastAddAtRef = useRef(0);

  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [viewport, setViewport] = useState<Viewport>({ x: 0, y: 0, zoom: 1 });
  const [icon, setIcon] = useState("layout");
  const [settings, setSettings] = useState<Record<string, unknown>>({});
  const [logs, setLogs] = useState<Record<string, unknown>[]>([]);
  const [updatedAt, setUpdatedAt] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [flowViewport, setFlowViewport] = useState<Viewport | undefined>();
  const fileRef = useRef<HTMLInputElement>(null);

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
    setLogs(canvas.logs ?? []);
    setUpdatedAt(canvas.updated_at ?? 0);
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
      nodes: flowNodesToLegacy(nodes),
      connections: flowEdgesToLegacy(edges),
      viewport: flowViewportToLegacy(viewport),
      logs,
      settings,
      base_updated_at: updatedAt,
      client_id: CLIENT_ID,
    });
  }, [id, title, icon, nodes, edges, viewport, logs, settings, updatedAt, saveMutation]);

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

  const screenToFlowPosition = useCallback((offset = 0) => {
    const cx = (-viewport.x + window.innerWidth / 2) / viewport.zoom;
    const cy = (-viewport.y + window.innerHeight / 2) / viewport.zoom;
    return { x: cx + offset, y: cy + offset };
  }, [viewport]);

  const addNode = useCallback(
    (type: Batch1NodeType, extra?: Record<string, unknown>) => {
      const now = Date.now();
      if (now - lastAddAtRef.current < 200) return;
      lastAddAtRef.current = now;
      const offset = nodes.length * 24;
      const pos = screenToFlowPosition(offset);
      const legacy = createCanvasNode(type, pos.x, pos.y);
      const flowNodes = legacyNodesToFlow([{ ...legacy, ...extra }]);
      setNodes((prev) => [...prev, ...flowNodes]);
      scheduleSave();
    },
    [nodes.length, screenToFlowPosition, scheduleSave],
  );

  const updateNodeData = useCallback(
    (nodeId: string, patch: Record<string, unknown>) => {
      setNodes((prev) =>
        prev.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, ...patch } } : n)),
      );
      scheduleSave();
    },
    [scheduleSave],
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
      <CanvasEditorActionsProvider value={{ updateNodeData }}>
        <div className="flex flex-1 min-h-0">
          <CanvasFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={setNodes}
          onEdgesChange={setEdges}
          onViewportChange={setViewport}
          initialViewport={flowViewport}
          onDirty={scheduleSave}
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

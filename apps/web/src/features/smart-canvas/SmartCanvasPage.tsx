import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  createSmartNode,
  fetchSmartCanvas,
  newSmartClientId,
  saveSmartCanvas,
  uploadSmartMedia,
} from "./api";
import { CreateFab, CreateMenu } from "./components/CreateMenu";
import { SmartCanvasViewport, viewportCenter } from "./components/SmartCanvasViewport";
import type { SmartCanvasData, SmartNode, SmartNodeType, SmartViewport } from "./types";

const CLIENT_ID = newSmartClientId();
const SAVE_DELAY_MS = 450;

export function SmartCanvasPage() {
  const { id = "" } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const viewportRef = useRef<HTMLDivElement>(null);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [nodes, setNodes] = useState<SmartNode[]>([]);
  const [viewport, setViewport] = useState<SmartViewport>({ x: 0, y: 0, scale: 1 });
  const [title, setTitle] = useState("智能画布");
  const [icon, setIcon] = useState("sparkles");
  const [settings, setSettings] = useState<Record<string, unknown>>({});
  const [connections, setConnections] = useState<Record<string, unknown>[]>([]);
  const [logs, setLogs] = useState<Record<string, unknown>[]>([]);
  const [updatedAt, setUpdatedAt] = useState(0);
  const [selectedId, setSelectedId] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "pending" | "saving" | "saved" | "error">("idle");
  const fileRef = useRef<HTMLInputElement>(null);
  const hydratedRef = useRef(false);
  const lastAddAtRef = useRef(0);

  const canvasQuery = useQuery({
    queryKey: ["smart-canvas", id],
    queryFn: () => fetchSmartCanvas(id),
    enabled: Boolean(id),
  });

  useEffect(() => {
    if (!canvasQuery.data || hydratedRef.current) return;
    const canvas = canvasQuery.data;
    setNodes(canvas.nodes);
    setViewport(canvas.viewport);
    setTitle(canvas.title || "智能画布");
    setIcon(canvas.icon || "sparkles");
    setSettings(canvas.settings ?? {});
    setConnections(canvas.connections ?? []);
    setLogs(canvas.logs ?? []);
    setUpdatedAt(canvas.updated_at ?? 0);
    hydratedRef.current = true;
  }, [canvasQuery.data]);

  useEffect(() => {
    hydratedRef.current = false;
    setSelectedId("");
    setSaveState("idle");
  }, [id]);

  const saveMutation = useMutation({
    mutationFn: (payload: Parameters<typeof saveSmartCanvas>[1]) => saveSmartCanvas(id, payload),
    onMutate: () => setSaveState("saving"),
    onSuccess: (canvas: SmartCanvasData) => {
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
      nodes,
      connections,
      viewport,
      logs,
      settings,
      base_updated_at: updatedAt,
      client_id: CLIENT_ID,
    });
  }, [id, title, icon, nodes, connections, viewport, logs, settings, updatedAt, saveMutation]);

  const scheduleSave = useCallback(() => {
    setSaveState("pending");
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => {
      flushSave();
    }, SAVE_DELAY_MS);
  }, [flushSave]);

  useEffect(
    () => () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    },
    [],
  );

  const addNode = (type: SmartNodeType, extra?: Partial<SmartNode>) => {
    const now = Date.now();
    if (now - lastAddAtRef.current < 200) return;
    lastAddAtRef.current = now;
    const rect = viewportRef.current?.getBoundingClientRect();
    const center = viewportCenter(viewport, rect);
    const offset = nodes.length * 24;
    const node = createSmartNode(type, center.x + offset, center.y + offset, extra);
    setNodes((prev) => [...prev, node]);
    setSelectedId(node.id);
    scheduleSave();
  };

  const deleteSelected = useCallback(() => {
    if (!selectedId) return;
    setNodes((prev) => prev.filter((n) => n.id !== selectedId));
    setSelectedId("");
    scheduleSave();
  }, [selectedId, scheduleSave]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "Delete" || e.key === "Backspace") {
        e.preventDefault();
        deleteSelected();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [deleteSelected]);

  const uploadMutation = useMutation({
    mutationFn: uploadSmartMedia,
    onSuccess: (items) => {
      addNode("smart-image", { images: items, title: items.length > 1 ? "Group" : "Image" });
      toast.success("已上传");
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "上传失败"),
  });

  const saveLabel =
    saveState === "saving"
      ? "保存中…"
      : saveState === "pending"
        ? "待保存"
        : saveState === "saved"
          ? "已保存"
          : saveState === "error"
            ? "保存失败"
            : "未修改";

  if (canvasQuery.isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 size-5 animate-spin" />
        加载智能画布…
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
    <div data-testid="smart-canvas-page" className="flex h-full min-h-0 flex-col">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-card/80 px-4 backdrop-blur">
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
              scheduleSave();
            }}
            className="h-8 max-w-[240px] border-none bg-transparent px-1 text-sm font-semibold shadow-none focus-visible:ring-0"
            aria-label="画布标题"
          />
        </div>
        <div className="flex items-center gap-2">
          {selectedId ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="text-destructive"
              data-testid="smart-delete-selected"
              onClick={deleteSelected}
            >
              <Trash2 className="size-4" />
              删除
            </Button>
          ) : null}
          <span
            className={`text-xs ${
              saveState === "error" ? "text-destructive" : "text-muted-foreground"
            }`}
            data-testid="smart-save-status"
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
            {saveLabel}
          </span>
        </div>
      </header>

      <div ref={viewportRef} className="relative flex-1 min-h-0">
        <SmartCanvasViewport
          nodes={nodes}
          viewport={viewport}
          selectedId={selectedId}
          onViewportChange={setViewport}
          onNodesChange={setNodes}
          onSelect={setSelectedId}
          onDelete={(nodeId) => {
            setNodes((prev) => prev.filter((n) => n.id !== nodeId));
            if (selectedId === nodeId) setSelectedId("");
            scheduleSave();
          }}
          onTextChange={(nodeId, text) => {
            setNodes((prev) => prev.map((n) => (n.id === nodeId ? { ...n, text } : n)));
          }}
          onBackgroundClick={() => setSelectedId("")}
          onDirty={scheduleSave}
        />

        <CreateMenu
          open={createOpen}
          onOpenChange={setCreateOpen}
          onCreate={(type) => addNode(type)}
          onUpload={() => fileRef.current?.click()}
        />
        <CreateFab onClick={() => setCreateOpen(true)} />
      </div>

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

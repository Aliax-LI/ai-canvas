import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Layers, Loader2, Plus, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import {
  createCanvas,
  createProject,
  deleteCanvas,
  deleteProject,
  fetchCanvases,
  fetchProjects,
  fetchTrashCanvases,
  purgeCanvas,
  restoreCanvas,
} from "./api";
import type { CanvasRecord } from "./types";

const PROJECT_KEY = "canvasListCurrentProjectId";

function rememberedProjectId(): string {
  try {
    return localStorage.getItem(PROJECT_KEY) || "default";
  } catch {
    return "default";
  }
}

function formatTime(value: number): string {
  if (!value) return "--";
  const ms = value < 10_000_000_000 ? value * 1000 : value;
  return new Date(ms).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function canvasHref(canvas: CanvasRecord): string {
  return canvas.kind === "smart" ? `/smart/${canvas.id}` : `/canvas/${canvas.id}`;
}

export function CanvasListPage() {
  const queryClient = useQueryClient();
  const [projectId, setProjectId] = useState(rememberedProjectId);
  const [showTrash, setShowTrash] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");

  const projectsQuery = useQuery({ queryKey: ["projects"], queryFn: fetchProjects });
  const canvasesQuery = useQuery({ queryKey: ["canvases"], queryFn: fetchCanvases });
  const trashQuery = useQuery({
    queryKey: ["canvases-trash"],
    queryFn: fetchTrashCanvases,
    enabled: showTrash,
  });

  const projects = projectsQuery.data ?? [];
  const canvases = canvasesQuery.data ?? [];

  const projectCanvases = useMemo(
    () => canvases.filter((c) => (c.project || "default") === projectId),
    [canvases, projectId],
  );

  const selectProject = (id: string) => {
    setProjectId(id);
    try {
      localStorage.setItem(PROJECT_KEY, id);
    } catch {
      /* ignore */
    }
  };

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["canvases"] });
    void queryClient.invalidateQueries({ queryKey: ["projects"] });
    void queryClient.invalidateQueries({ queryKey: ["canvases-trash"] });
  };

  const createCanvasMutation = useMutation({
    mutationFn: () =>
      createCanvas({
        title: "未命名画布",
        project: projectId,
        board_x: 120 + projectCanvases.length * 24,
        board_y: 120 + projectCanvases.length * 24,
      }),
    onSuccess: () => {
      toast.success("已创建画布");
      invalidate();
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "创建失败"),
  });

  const createProjectMutation = useMutation({
    mutationFn: () => createProject(newProjectName.trim() || "新项目"),
    onSuccess: (project) => {
      setNewProjectName("");
      selectProject(project.id);
      toast.success("项目已创建");
      invalidate();
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "创建失败"),
  });

  const deleteCanvasMutation = useMutation({
    mutationFn: deleteCanvas,
    onSuccess: () => {
      toast.success("画布已移入回收站");
      invalidate();
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "删除失败"),
  });

  const deleteProjectMutation = useMutation({
    mutationFn: deleteProject,
    onSuccess: () => {
      selectProject("default");
      toast.success("项目已删除");
      invalidate();
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "删除失败"),
  });

  const restoreMutation = useMutation({
    mutationFn: restoreCanvas,
    onSuccess: () => {
      toast.success("画布已恢复");
      invalidate();
    },
  });

  const purgeMutation = useMutation({
    mutationFn: purgeCanvas,
    onSuccess: () => {
      toast.success("画布已永久删除");
      invalidate();
    },
  });

  const loading = projectsQuery.isLoading || canvasesQuery.isLoading;
  const currentProject = projects.find((p) => p.id === projectId);

  return (
    <div className="flex h-[calc(100vh-8rem)] min-h-[520px] flex-col gap-4" data-testid="canvas-list-page">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">无限画布</h1>
          <p className="text-sm text-muted-foreground">
            {currentProject?.name ?? projectId} · {projectCanvases.length} 个画布
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" size="sm" onClick={() => invalidate()}>
            <RefreshCw />
            刷新
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setShowTrash((v) => !v)}
          >
            <Trash2 />
            回收站
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={() => createCanvasMutation.mutate()}
            disabled={createCanvasMutation.isPending}
          >
            {createCanvasMutation.isPending ? <Loader2 className="animate-spin" /> : <Plus />}
            新建画布
          </Button>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="flex flex-col gap-3 rounded-lg border border-border bg-card p-3">
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">项目</div>
          <div className="flex max-h-64 flex-col gap-1 overflow-y-auto">
            {projects.map((project) => (
              <button
                key={project.id}
                type="button"
                onClick={() => selectProject(project.id)}
                className={`rounded-md px-3 py-2 text-left text-sm transition-colors ${
                  projectId === project.id ? "bg-accent font-medium" : "hover:bg-muted/80"
                }`}
              >
                {project.name}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              placeholder="新项目名称"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              className="h-8 text-xs"
            />
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => createProjectMutation.mutate()}
              disabled={createProjectMutation.isPending}
            >
              <Plus />
            </Button>
          </div>
          {projectId !== "default" ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="text-destructive"
              onClick={() => deleteProjectMutation.mutate(projectId)}
            >
              删除当前项目
            </Button>
          ) : null}
        </aside>

        <section className="min-h-0 overflow-auto rounded-lg border border-border bg-[var(--canvas-bg)] p-6">
          {loading ? (
            <div className="flex items-center justify-center py-20 text-muted-foreground">
              <Loader2 className="mr-2 size-5 animate-spin" />
              加载中…
            </div>
          ) : showTrash ? (
            <TrashPanel
              items={trashQuery.data ?? []}
              loading={trashQuery.isLoading}
              onRestore={(id) => restoreMutation.mutate(id)}
              onPurge={(id) => purgeMutation.mutate(id)}
            />
          ) : projectCanvases.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-4 py-20 text-muted-foreground">
              <Layers className="size-12 opacity-40" />
              <p>此项目还没有画布</p>
              <Button type="button" onClick={() => createCanvasMutation.mutate()}>
                创建第一个画布
              </Button>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {projectCanvases.map((canvas) => (
                <CanvasCard
                  key={canvas.id}
                  canvas={canvas}
                  onDelete={() => deleteCanvasMutation.mutate(canvas.id)}
                />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function CanvasCard({ canvas, onDelete }: { canvas: CanvasRecord; onDelete: () => void }) {
  return (
    <Card className="group overflow-hidden transition-shadow hover:shadow-md">
      <CardContent className="p-0">
        <Link to={canvasHref(canvas)} className="block p-4">
          <div className="mb-3 flex items-start justify-between gap-2">
            <span className="text-2xl">{canvas.icon || "🧩"}</span>
            {canvas.pinned ? (
              <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                置顶
              </span>
            ) : null}
          </div>
          <h3 className="truncate font-medium">{canvas.title}</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {canvas.kind === "smart" ? "智能画布" : "无限画布"} · {canvas.node_count ?? 0} 节点
          </p>
          <p className="mt-1 text-xs text-muted-foreground">{formatTime(canvas.updated_at)}</p>
        </Link>
        <div className="flex justify-end border-t border-border px-3 py-2 opacity-0 transition-opacity group-hover:opacity-100">
          <Button type="button" variant="ghost" size="sm" className="text-destructive" onClick={onDelete}>
            删除
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function TrashPanel({
  items,
  loading,
  onRestore,
  onPurge,
}: {
  items: CanvasRecord[];
  loading: boolean;
  onRestore: (id: string) => void;
  onPurge: (id: string) => void;
}) {
  if (loading) {
    return (
      <div className="flex justify-center py-12 text-muted-foreground">
        <Loader2 className="size-5 animate-spin" />
      </div>
    );
  }
  if (!items.length) {
    return <p className="py-12 text-center text-sm text-muted-foreground">回收站为空</p>;
  }
  return (
    <div className="space-y-3" data-testid="canvas-trash-panel">
      {items.map((canvas) => (
        <div
          key={canvas.id}
          className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card px-4 py-3"
        >
          <div>
            <div className="font-medium">{canvas.title}</div>
            <div className="text-xs text-muted-foreground">删除于 {formatTime(canvas.deleted_at ?? 0)}</div>
          </div>
          <div className="flex gap-2">
            <Button type="button" size="sm" variant="outline" onClick={() => onRestore(canvas.id)}>
              恢复
            </Button>
            <Button type="button" size="sm" variant="destructive" onClick={() => onPurge(canvas.id)}>
              永久删除
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}

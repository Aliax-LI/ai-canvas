import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus, Save, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";
import { ApiError } from "@infinite-canvas/api-types/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  deleteWorkflow,
  fetchComfyInstances,
  fetchWorkflow,
  fetchWorkflows,
  saveComfyInstances,
  saveWorkflowConfig,
  uploadWorkflow,
} from "./api";
import { SettingsPageLayout } from "./components/SettingsPageLayout";
import { FieldRow } from "./components/ModelListEditor";
import type { WorkflowConfig, WorkflowField, WorkflowSummary } from "./types";

function errorMessage(err: unknown): string {
  if (err instanceof ApiError && err.body && typeof err.body === "object" && "detail" in err.body) {
    const detail = (err.body as { detail: unknown }).detail;
    return typeof detail === "string" ? detail : JSON.stringify(detail);
  }
  return err instanceof Error ? err.message : "请求失败";
}

const FIELD_TYPES = [
  { value: "text", label: "文本" },
  { value: "textarea", label: "多行文本" },
  { value: "number", label: "数字" },
  { value: "slider", label: "滑块" },
  { value: "dropdown", label: "下拉框" },
  { value: "image", label: "图片" },
  { value: "video", label: "视频" },
  { value: "audio", label: "音频" },
  { value: "boolean", label: "开关" },
];

export function ComfyuiSettingsPage() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: serverInstances = [], isLoading: instancesLoading } = useQuery({
    queryKey: ["comfy-instances"],
    queryFn: fetchComfyInstances,
  });

  const { data: workflows = [], isLoading: workflowsLoading } = useQuery({
    queryKey: ["workflows"],
    queryFn: fetchWorkflows,
  });

  const [instances, setInstances] = useState<string[]>([]);
  const [selectedName, setSelectedName] = useState("");
  const [config, setConfig] = useState<WorkflowConfig>({ title: "", fields: [] });
  const [status, setStatus] = useState("");

  useEffect(() => {
    if (serverInstances.length || serverInstances.length === 0) {
      setInstances(serverInstances.length ? serverInstances : ["127.0.0.1:8188"]);
    }
  }, [serverInstances]);

  useEffect(() => {
    if (workflows.length && !selectedName) {
      setSelectedName(workflows[0]?.name ?? "");
    }
  }, [workflows, selectedName]);

  const selectedWorkflow = useMemo(
    () => workflows.find((w) => w.name === selectedName) ?? null,
    [workflows, selectedName],
  );

  const workflowQuery = useQuery({
    queryKey: ["workflow", selectedName],
    queryFn: () => fetchWorkflow(selectedName),
    enabled: Boolean(selectedName),
  });

  useEffect(() => {
    if (workflowQuery.data?.config) {
      setConfig({
        title: workflowQuery.data.config.title || selectedWorkflow?.title || "",
        fields: workflowQuery.data.config.fields ?? [],
        mini_cards: workflowQuery.data.config.mini_cards,
      });
    }
  }, [workflowQuery.data, selectedWorkflow?.title]);

  const saveInstancesMutation = useMutation({
    mutationFn: () => saveComfyInstances(instances.filter(Boolean)),
    onSuccess: () => {
      toast.success("ComfyUI 后端地址已保存");
      setStatus("实例已保存");
      void queryClient.invalidateQueries({ queryKey: ["comfy-instances"] });
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const saveConfigMutation = useMutation({
    mutationFn: () => saveWorkflowConfig(selectedName, config),
    onSuccess: () => {
      toast.success("工作流配置已保存");
      setStatus("配置已保存");
      void queryClient.invalidateQueries({ queryKey: ["workflows"] });
      void queryClient.invalidateQueries({ queryKey: ["workflow", selectedName] });
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteWorkflow(selectedName),
    onSuccess: () => {
      toast.success("工作流已删除");
      setSelectedName("");
      void queryClient.invalidateQueries({ queryKey: ["workflows"] });
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const text = await file.text();
      const workflow = JSON.parse(text) as Record<string, unknown>;
      const name = file.name.replace(/\.json$/i, "") || `workflow-${Date.now()}`;
      return uploadWorkflow(name, workflow);
    },
    onSuccess: () => {
      toast.success("工作流已上传");
      void queryClient.invalidateQueries({ queryKey: ["workflows"] });
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const patchField = (index: number, patch: Partial<WorkflowField>) => {
    setConfig((prev) => ({
      ...prev,
      fields: prev.fields.map((f, i) => (i === index ? { ...f, ...patch } : f)),
    }));
  };

  const addField = () => {
    setConfig((prev) => ({
      ...prev,
      fields: [
        ...prev.fields,
        {
          id: `field_${Date.now()}`,
          node: "",
          input: "",
          name: "新字段",
          type: "text",
        },
      ],
    }));
  };

  const removeField = (index: number) => {
    setConfig((prev) => ({
      ...prev,
      fields: prev.fields.filter((_, i) => i !== index),
    }));
  };

  const isLoading = instancesLoading || workflowsLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-muted-foreground">
        <Loader2 className="mr-2 size-5 animate-spin" />
        加载工作流设置…
      </div>
    );
  }

  return (
    <SettingsPageLayout
      title="工作流设置"
      description="配置 ComfyUI 后端地址，选择本地工作流并暴露画布输入参数。"
      status={status}
      sidebar={
        <div className="flex flex-col gap-4">
          <div className="space-y-2">
            <div className="px-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              ComfyUI 后端
            </div>
            {instances.map((inst, index) => (
              <Input
                key={index}
                value={inst}
                onChange={(e) =>
                  setInstances((prev) => prev.map((v, i) => (i === index ? e.target.value : v)))
                }
                placeholder="127.0.0.1:8188"
                className="font-mono text-xs"
              />
            ))}
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="flex-1"
                onClick={() => setInstances((prev) => [...prev, "127.0.0.1:8188"])}
              >
                <Plus />
                添加
              </Button>
              <Button
                type="button"
                size="sm"
                className="flex-1"
                onClick={() => saveInstancesMutation.mutate()}
                disabled={saveInstancesMutation.isPending}
              >
                <Save />
                保存
              </Button>
            </div>
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              格式：<span className="font-mono">host:port</span>
            </p>
          </div>

          <div className="space-y-2 border-t border-border pt-4">
            <div className="px-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              工作流列表
            </div>
            <div className="flex max-h-64 flex-col gap-1 overflow-y-auto" data-testid="workflow-list">
              {workflows.map((wf: WorkflowSummary) => (
                <button
                  key={wf.name}
                  type="button"
                  onClick={() => setSelectedName(wf.name)}
                  className={`rounded-md px-3 py-2 text-left text-sm transition-colors ${
                    selectedName === wf.name
                      ? "bg-accent font-medium"
                      : "hover:bg-muted/80"
                  }`}
                >
                  <div className="truncate">{wf.title || wf.name}</div>
                  <div className="truncate font-mono text-[10px] text-muted-foreground">{wf.name}</div>
                </button>
              ))}
              {!workflows.length ? (
                <p className="px-1 text-xs text-muted-foreground">暂无工作流，请上传 JSON</p>
              ) : null}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/json"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) uploadMutation.mutate(file);
                e.target.value = "";
              }}
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-full"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadMutation.isPending}
            >
              <Upload />
              上传工作流
            </Button>
          </div>
        </div>
      }
    >
      {selectedName ? (
        <div className="space-y-6" data-testid="workflow-editor">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">{config.title || selectedWorkflow?.title || selectedName}</h2>
              <p className="font-mono text-xs text-muted-foreground">{selectedName}</p>
            </div>
            <div className="flex gap-2">
              {!selectedWorkflow?.builtin ? (
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  onClick={() => deleteMutation.mutate()}
                  disabled={deleteMutation.isPending}
                >
                  <Trash2 />
                  删除
                </Button>
              ) : null}
              <Button
                type="button"
                size="sm"
                onClick={() => saveConfigMutation.mutate()}
                disabled={saveConfigMutation.isPending || workflowQuery.isLoading}
              >
                {saveConfigMutation.isPending ? <Loader2 className="animate-spin" /> : <Save />}
                保存配置
              </Button>
            </div>
          </div>

          {workflowQuery.isLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              加载工作流…
            </div>
          ) : null}

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">画布暴露字段</CardTitle>
              <CardDescription>勾选并命名将在 ComfyUI 画布节点上显示的输入控件</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <FieldRow label="显示标题">
                <Input
                  value={config.title}
                  onChange={(e) => setConfig((prev) => ({ ...prev, title: e.target.value }))}
                />
              </FieldRow>

              {config.fields.map((field, index) => (
                <div
                  key={field.id || index}
                  className="grid gap-3 rounded-lg border border-border p-4 md:grid-cols-2 lg:grid-cols-4"
                >
                  <FieldRow label="显示名">
                    <Input value={field.name} onChange={(e) => patchField(index, { name: e.target.value })} />
                  </FieldRow>
                  <FieldRow label="节点 ID">
                    <Input
                      value={field.node}
                      onChange={(e) => patchField(index, { node: e.target.value })}
                      className="font-mono text-xs"
                    />
                  </FieldRow>
                  <FieldRow label="输入名">
                    <Input
                      value={field.input}
                      onChange={(e) => patchField(index, { input: e.target.value })}
                      className="font-mono text-xs"
                    />
                  </FieldRow>
                  <FieldRow label="类型">
                    <select
                      className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                      value={field.type}
                      onChange={(e) => patchField(index, { type: e.target.value })}
                    >
                      {FIELD_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                  </FieldRow>
                  <div className="flex items-end md:col-span-2 lg:col-span-4">
                    <Button type="button" variant="ghost" size="sm" onClick={() => removeField(index)}>
                      移除字段
                    </Button>
                  </div>
                </div>
              ))}

              <Button type="button" variant="outline" size="sm" onClick={addField}>
                <Plus />
                添加字段
              </Button>
            </CardContent>
          </Card>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">从左侧选择工作流，或上传新的 API 工作流 JSON</p>
      )}
    </SettingsPageLayout>
  );
}

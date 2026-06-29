import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plug, Save, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { ApiError } from "@infinite-canvas/api-types/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  fetchProviders,
  fetchUpstreamModels,
  saveProviders,
  testProviderConnection,
} from "./api";
import { ProviderList } from "./components/ProviderList";
import { SettingsPageLayout } from "./components/SettingsPageLayout";
import { FieldRow, KeyField, ModelListEditor } from "./components/ModelListEditor";
import type { ApiProvider, SaveProviderPayload } from "./types";

const PROTOCOLS = [
  { value: "openai", label: "OpenAI 兼容" },
  { value: "apimart", label: "APIMart" },
  { value: "gemini", label: "Gemini" },
  { value: "volcengine", label: "火山引擎" },
  { value: "runninghub", label: "RunningHub" },
  { value: "modelscope", label: "ModelScope" },
];

const IMAGE_MODES = [
  { value: "openai", label: "OpenAI multipart" },
  { value: "openai-json", label: "OpenAI JSON" },
];

function slugifyId(name: string): string {
  return (
    name
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || `provider-${Date.now()}`
  );
}

function errorMessage(err: unknown): string {
  if (err instanceof ApiError && err.body && typeof err.body === "object" && "detail" in err.body) {
    const detail = (err.body as { detail: unknown }).detail;
    return typeof detail === "string" ? detail : JSON.stringify(detail);
  }
  return err instanceof Error ? err.message : "请求失败";
}

interface KeyDrafts {
  apiKey: string;
  walletKey: string;
  volcAk: string;
  volcSk: string;
  clearKey: boolean;
  clearWalletKey: boolean;
  clearVolcAk: boolean;
  clearVolcSk: boolean;
}

const emptyKeyDraft = (): KeyDrafts => ({
  apiKey: "",
  walletKey: "",
  volcAk: "",
  volcSk: "",
  clearKey: false,
  clearWalletKey: false,
  clearVolcAk: false,
  clearVolcSk: false,
});

export function ApiSettingsPage() {
  const queryClient = useQueryClient();
  const { data: serverProviders = [], isLoading, isError } = useQuery({
    queryKey: ["providers"],
    queryFn: fetchProviders,
  });

  const [providers, setProviders] = useState<ApiProvider[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [keyDrafts, setKeyDrafts] = useState<Record<string, KeyDrafts>>({});
  const [status, setStatus] = useState("");

  useEffect(() => {
    if (serverProviders.length) {
      setProviders(serverProviders);
      setSelectedId((prev) => prev || serverProviders[0]?.id || "");
    }
  }, [serverProviders]);

  const selected = useMemo(
    () => providers.find((p) => p.id === selectedId) ?? null,
    [providers, selectedId],
  );

  const keyDraft = keyDrafts[selectedId] ?? emptyKeyDraft();

  const patchSelected = useCallback(
    (patch: Partial<ApiProvider>) => {
      if (!selectedId) return;
      setProviders((prev) =>
        prev.map((p) => (p.id === selectedId ? { ...p, ...patch } : p)),
      );
    },
    [selectedId],
  );

  const patchKeyDraft = useCallback(
    (patch: Partial<KeyDrafts>) => {
      if (!selectedId) return;
      setKeyDrafts((prev) => ({
        ...prev,
        [selectedId]: { ...(prev[selectedId] ?? emptyKeyDraft()), ...patch },
      }));
    },
    [selectedId],
  );

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload: SaveProviderPayload[] = providers.map((p) => {
        const draft = keyDrafts[p.id] ?? emptyKeyDraft();
        const item: SaveProviderPayload = { ...p };
        if (draft.clearKey) item.clear_key = true;
        else if (draft.apiKey.trim()) item.api_key = draft.apiKey.trim();
        if (p.id === "runninghub") {
          if (draft.clearWalletKey) item.clear_wallet_key = true;
          else if (draft.walletKey.trim()) item.wallet_api_key = draft.walletKey.trim();
        }
        if (p.id === "volcengine") {
          if (draft.clearVolcAk) item.clear_volcengine_access_key_id = true;
          else if (draft.volcAk.trim()) item.volcengine_access_key_id = draft.volcAk.trim();
          if (draft.clearVolcSk) item.clear_volcengine_secret_access_key = true;
          else if (draft.volcSk.trim()) item.volcengine_secret_access_key = draft.volcSk.trim();
        }
        return item;
      });
      return saveProviders(payload);
    },
    onSuccess: (saved) => {
      setProviders(saved);
      setKeyDrafts({});
      setStatus("已保存");
      toast.success("API 设置已保存");
      void queryClient.invalidateQueries({ queryKey: ["providers"] });
    },
    onError: (err) => {
      toast.error(errorMessage(err));
    },
  });

  const testMutation = useMutation({
    mutationFn: async () => {
      if (!selected) throw new Error("未选择平台");
      const draft = keyDrafts[selected.id] ?? emptyKeyDraft();
      return testProviderConnection({
        provider_id: selected.id,
        base_url: selected.base_url,
        protocol: selected.protocol,
        image_request_mode: selected.image_request_mode,
        api_key: draft.apiKey.trim(),
      });
    },
    onSuccess: () => {
      toast.success("连接测试成功");
      setStatus("连接正常");
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const fetchModelsMutation = useMutation({
    mutationFn: async () => {
      if (!selected) throw new Error("未选择平台");
      const draft = keyDrafts[selected.id] ?? emptyKeyDraft();
      return fetchUpstreamModels({
        provider_id: selected.id,
        base_url: selected.base_url,
        protocol: selected.protocol,
        image_request_mode: selected.image_request_mode,
        api_key: draft.apiKey.trim(),
      });
    },
    onSuccess: (data) => {
      if (!selected || !data || typeof data !== "object") {
        toast.message("已请求上游模型列表");
        return;
      }
      const record = data as Record<string, unknown>;
      patchSelected({
        image_models: Array.isArray(record.image_models) ? (record.image_models as string[]) : selected.image_models,
        chat_models: Array.isArray(record.chat_models) ? (record.chat_models as string[]) : selected.chat_models,
        video_models: Array.isArray(record.video_models) ? (record.video_models as string[]) : selected.video_models,
      });
      toast.success("已从上游拉取模型列表");
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const handleAdd = () => {
    const name = "新平台";
    const id = slugifyId(name);
    const next: ApiProvider = {
      id,
      name,
      base_url: "https://api.example.com/v1",
      protocol: "openai",
      image_request_mode: "openai",
      enabled: true,
      primary: false,
      image_models: [],
      chat_models: [],
      video_models: [],
    };
    setProviders((prev) => [...prev, next]);
    setSelectedId(id);
  };

  const handleDelete = () => {
    if (!selected || providers.length <= 1) {
      toast.error("至少保留一个 API 平台");
      return;
    }
    setProviders((prev) => prev.filter((p) => p.id !== selected.id));
    setSelectedId(providers.find((p) => p.id !== selected.id)?.id ?? "");
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-muted-foreground">
        <Loader2 className="mr-2 size-5 animate-spin" />
        加载 API 设置…
      </div>
    );
  }

  if (isError) {
    return (
      <div className="py-12 text-center text-sm text-destructive">
        无法加载 API 设置，请确认后端已启动（端口 3000）。
      </div>
    );
  }

  return (
    <SettingsPageLayout
      title="API 设置"
      description="管理平台地址、模型列表和 Key。Key 写入后端 env，页面不会回显完整内容。"
      status={status}
      sidebar={
        <ProviderList
          providers={providers}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onAdd={handleAdd}
        />
      }
    >
      {selected ? (
        <div className="space-y-6" data-testid="provider-editor">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">{selected.name || "未命名平台"}</h2>
              <p className="text-xs font-mono text-muted-foreground">ID: {selected.id}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => testMutation.mutate()}
                disabled={testMutation.isPending}
              >
                {testMutation.isPending ? <Loader2 className="animate-spin" /> : <Plug />}
                测试连接
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fetchModelsMutation.mutate()}
                disabled={fetchModelsMutation.isPending}
              >
                拉取模型
              </Button>
              <Button type="button" variant="destructive" size="sm" onClick={handleDelete}>
                <Trash2 />
                删除
              </Button>
              <Button type="button" size="sm" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
                {saveMutation.isPending ? <Loader2 className="animate-spin" /> : <Save />}
                保存
              </Button>
            </div>
          </div>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">基本信息</CardTitle>
              <CardDescription>平台显示名、唯一 ID 和请求地址</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <FieldRow label="平台名称">
                <Input
                  value={selected.name}
                  onChange={(e) => patchSelected({ name: e.target.value })}
                />
              </FieldRow>
              <FieldRow label="平台 ID" hint="保存后不建议修改">
                <Input
                  value={selected.id}
                  onChange={(e) => {
                    const newId = slugifyId(e.target.value);
                    setProviders((prev) =>
                      prev.map((p) => (p.id === selectedId ? { ...p, id: newId } : p)),
                    );
                    setSelectedId(newId);
                  }}
                  className="font-mono text-sm"
                />
              </FieldRow>
              <div className="md:col-span-2">
                <FieldRow label="请求地址">
                  <Input
                    value={selected.base_url}
                    onChange={(e) => patchSelected({ base_url: e.target.value })}
                    className="font-mono text-sm"
                  />
                </FieldRow>
              </div>
              <FieldRow label="协议">
                <select
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={selected.protocol}
                  onChange={(e) => patchSelected({ protocol: e.target.value })}
                >
                  {PROTOCOLS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </FieldRow>
              <FieldRow label="图片请求模式">
                <select
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={selected.image_request_mode}
                  onChange={(e) => patchSelected({ image_request_mode: e.target.value })}
                >
                  {IMAGE_MODES.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </FieldRow>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={selected.enabled}
                  onChange={(e) => patchSelected({ enabled: e.target.checked })}
                />
                启用此平台
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={selected.primary}
                  onChange={(e) =>
                    setProviders((prev) =>
                      prev.map((p) => ({
                        ...p,
                        primary: p.id === selected.id ? e.target.checked : false,
                      })),
                    )
                  }
                />
                设为默认平台
              </label>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">API Key</CardTitle>
              <CardDescription>
                {selected.has_key
                  ? `已配置（${selected.key_preview ?? "****"}）— 留空则保持不变`
                  : "尚未配置 Key"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <KeyField
                label={selected.id === "runninghub" ? "RH币 API Key" : "API Key"}
                value={keyDraft.apiKey}
                onChange={(v) => patchKeyDraft({ apiKey: v, clearKey: false })}
              />
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => patchKeyDraft({ apiKey: "", clearKey: true })}
                >
                  清除 Key
                </Button>
              </div>

              {selected.id === "runninghub" ? (
                <>
                  <KeyField
                    label="账户余额 API Key（可选）"
                    hint={
                      selected.has_wallet_key
                        ? `已配置 ${selected.wallet_key_preview ?? ""}`
                        : undefined
                    }
                    value={keyDraft.walletKey}
                    onChange={(v) => patchKeyDraft({ walletKey: v, clearWalletKey: false })}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => patchKeyDraft({ walletKey: "", clearWalletKey: true })}
                  >
                    清除余额 Key
                  </Button>
                </>
              ) : null}

              {selected.id === "volcengine" ? (
                <>
                  <KeyField
                    label="素材库 Access Key ID"
                    hint={selected.volcengine_access_key_preview}
                    value={keyDraft.volcAk}
                    onChange={(v) => patchKeyDraft({ volcAk: v, clearVolcAk: false })}
                  />
                  <KeyField
                    label="素材库 Secret Access Key"
                    hint={selected.volcengine_secret_key_preview}
                    value={keyDraft.volcSk}
                    onChange={(v) => patchKeyDraft({ volcSk: v, clearVolcSk: false })}
                  />
                  <div className="grid gap-4 md:grid-cols-2">
                    <FieldRow label="ProjectName">
                      <Input
                        value={selected.volcengine_project_name ?? "default"}
                        onChange={(e) => patchSelected({ volcengine_project_name: e.target.value })}
                      />
                    </FieldRow>
                    <FieldRow label="Region">
                      <Input
                        value={selected.volcengine_region ?? "cn-beijing"}
                        onChange={(e) => patchSelected({ volcengine_region: e.target.value })}
                      />
                    </FieldRow>
                  </div>
                </>
              ) : null}

              {selected.id === "jimeng" ? (
                <p className="text-sm text-muted-foreground">
                  即梦使用本机 CLI 登录，请在终端执行 <code className="font-mono">dreamina login</code>，或通过
                  画布/API 调用 <code className="font-mono">/api/jimeng/*</code> 端点管理会话。
                </p>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">模型列表</CardTitle>
              <CardDescription>每行一个模型 ID，保存后写入平台配置</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 lg:grid-cols-3">
              <ModelListEditor
                label="图像模型"
                value={selected.image_models}
                onChange={(image_models) => patchSelected({ image_models })}
              />
              <ModelListEditor
                label="对话模型"
                value={selected.chat_models}
                onChange={(chat_models) => patchSelected({ chat_models })}
              />
              <ModelListEditor
                label="视频模型"
                value={selected.video_models}
                onChange={(video_models) => patchSelected({ video_models })}
              />
            </CardContent>
          </Card>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">请从左侧选择一个平台</p>
      )}
    </SettingsPageLayout>
  );
}

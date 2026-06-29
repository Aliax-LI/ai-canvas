import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ImagePlus, Loader2, Zap } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/client";
import { deleteHistory, fetchHistory, onlineGenerate, uploadAiReferences } from "./api";
import { HistoryMasonry } from "./components/HistoryMasonry";
import { ToolLayout } from "./components/ToolLayout";
import type { AiConfig } from "../chat/types";

const SIZES = ["1024x1024", "1536x1024", "1024x1536", "1792x1024", "1024x1792"];

export function OnlineToolPage() {
  const queryClient = useQueryClient();
  const [prompt, setPrompt] = useState("");
  const [providerId, setProviderId] = useState("");
  const [model, setModel] = useState("");
  const [size, setSize] = useState("1024x1024");
  const [quality, setQuality] = useState("auto");
  const [refs, setRefs] = useState<{ url: string; name: string }[]>([]);
  const [resultUrl, setResultUrl] = useState("");

  const configQuery = useQuery({ queryKey: ["ai-config"], queryFn: () => api.get<AiConfig>("/config") });
  const historyQuery = useQuery({ queryKey: ["history", "online"], queryFn: () => fetchHistory("online") });

  useEffect(() => {
    const cfg = configQuery.data;
    if (!cfg || providerId) return;
    const p = cfg.api_providers.find((x) => x.primary) ?? cfg.api_providers[0];
    if (p) {
      setProviderId(p.id);
      setModel(p.image_models?.[0] ?? cfg.image_models?.[0] ?? "");
    }
  }, [configQuery.data, providerId]);

  const generateMutation = useMutation({
    mutationFn: async () => {
      if (!prompt.trim()) throw new Error("请输入提示词");
      return onlineGenerate({
        prompt: prompt.trim(),
        provider_id: providerId,
        model,
        size,
        quality,
        n: 1,
        reference_images: refs.map((r) => ({ url: r.url, name: r.name, role: "", kind: "image" })),
      });
    },
    onSuccess: (data) => {
      const url = data.images?.[0];
      if (url) {
        setResultUrl(url);
        toast.success("生成完成");
        void queryClient.invalidateQueries({ queryKey: ["history", "online"] });
      }
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "生成失败"),
  });

  const uploadMutation = useMutation({
    mutationFn: (files: File[]) => uploadAiReferences(files),
    onSuccess: (files) => {
      setRefs((prev) => [...prev, ...files].slice(0, 4));
      toast.success("参考图已上传");
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "上传失败"),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteHistory,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["history", "online"] }),
  });

  const providers = configQuery.data?.api_providers ?? [];
  const imageModels =
    providers.find((p) => p.id === providerId)?.image_models ??
    configQuery.data?.image_models ??
    [];

  return (
    <ToolLayout
      title="在线生图"
      subtitle="通过 API 提供商在线生成图片"
      testId="tool-online"
      controls={
        <>
          <div className="space-y-2">
            <Label>平台</Label>
            <select
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={providerId}
              onChange={(e) => {
                setProviderId(e.target.value);
                const p = providers.find((x) => x.id === e.target.value);
                setModel(p?.image_models?.[0] ?? configQuery.data?.image_models?.[0] ?? "");
              }}
            >
              {providers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name || p.id}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <Label>模型</Label>
            <select
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={model}
              onChange={(e) => setModel(e.target.value)}
            >
              {imageModels.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>尺寸</Label>
              <select
                className="flex h-9 w-full rounded-md border border-input bg-background px-2 text-xs"
                value={size}
                onChange={(e) => setSize(e.target.value)}
              >
                {SIZES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label>质量</Label>
              <select
                className="flex h-9 w-full rounded-md border border-input bg-background px-2 text-xs"
                value={quality}
                onChange={(e) => setQuality(e.target.value)}
              >
                {["auto", "low", "medium", "high"].map((q) => (
                  <option key={q} value={q}>
                    {q}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="space-y-2">
            <Label>提示词</Label>
            <Textarea rows={4} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>参考图（可选）</Label>
            <input
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              id="online-ref-upload"
              onChange={(e) => {
                const files = [...(e.target.files ?? [])];
                if (files.length) uploadMutation.mutate(files);
                e.target.value = "";
              }}
            />
            <Button type="button" variant="outline" size="sm" className="w-full" asChild>
              <label htmlFor="online-ref-upload" className="cursor-pointer">
                <ImagePlus />
                上传参考图 ({refs.length}/4)
              </label>
            </Button>
          </div>
          <Button
            type="button"
            className="w-full"
            disabled={generateMutation.isPending}
            onClick={() => generateMutation.mutate()}
          >
            {generateMutation.isPending ? <Loader2 className="animate-spin" /> : <Zap />}
            生成
          </Button>
        </>
      }
      result={
        resultUrl ? (
          <img src={resultUrl} alt="result" className="mx-auto max-h-[480px] rounded-xl border object-contain" />
        ) : (
          <div className="flex aspect-video items-center justify-center rounded-xl border border-dashed text-sm text-muted-foreground">
            生成结果
          </div>
        )
      }
      history={
        <HistoryMasonry
          items={historyQuery.data ?? []}
          loading={historyQuery.isLoading}
          onDelete={(ts) => deleteMutation.mutate(ts)}
        />
      }
    />
  );
}

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Zap } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  cloudGenerate,
  comfyGenerate,
  deleteHistory,
  fetchHistory,
  fetchModelScopeToken,
  newClientId,
} from "./api";
import { HistoryMasonry } from "./components/HistoryMasonry";
import { ToolLayout } from "./components/ToolLayout";

const CLIENT_ID = newClientId();

export function ZImageToolPage() {
  const queryClient = useQueryClient();
  const [engine, setEngine] = useState<"local" | "cloud">("local");
  const [prompt, setPrompt] = useState("");
  const [width, setWidth] = useState(1024);
  const [height, setHeight] = useState(1024);
  const [resultUrl, setResultUrl] = useState("");

  const historyQuery = useQuery({ queryKey: ["history", "zimage"], queryFn: () => fetchHistory("zimage") });

  const generateMutation = useMutation({
    mutationFn: async () => {
      if (!prompt.trim()) throw new Error("请输入提示词");
      if (engine === "local") {
        return comfyGenerate({
          prompt: prompt.trim(),
          width,
          height,
          type: "zimage",
          workflow_json: "Z-Image.json",
          client_id: CLIENT_ID,
        });
      }
      const token = await fetchModelScopeToken();
      return cloudGenerate({
        prompt: prompt.trim(),
        api_key: token,
        resolution: `${width}x${height}`,
        type: "zimage",
        client_id: CLIENT_ID,
      });
    },
    onSuccess: (data) => {
      const url = data.images?.[0] ?? data.url;
      if (url) {
        setResultUrl(url);
        toast.success("生成完成");
        void queryClient.invalidateQueries({ queryKey: ["history", "zimage"] });
      } else {
        toast.error(data.error ?? "未返回图片");
      }
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "生成失败"),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteHistory,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["history", "zimage"] }),
  });

  return (
    <ToolLayout
      title="文生图"
      subtitle="Z-Image 本地 ComfyUI 或 ModelScope 云端"
      testId="tool-zimage"
      controls={
        <>
          <div className="flex gap-2 rounded-lg bg-muted p-1">
            {(["local", "cloud"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setEngine(mode)}
                className={`flex-1 rounded-md py-1.5 text-xs font-medium ${
                  engine === mode ? "bg-background shadow-sm" : "text-muted-foreground"
                }`}
              >
                {mode === "local" ? "本地" : "云端"}
              </button>
            ))}
          </div>
          <div className="space-y-2">
            <Label>提示词</Label>
            <Textarea rows={4} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>宽度</Label>
              <Input type="number" value={width} onChange={(e) => setWidth(Number(e.target.value))} />
            </div>
            <div className="space-y-2">
              <Label>高度</Label>
              <Input type="number" value={height} onChange={(e) => setHeight(Number(e.target.value))} />
            </div>
          </div>
          <Button
            type="button"
            className="w-full"
            disabled={generateMutation.isPending}
            onClick={() => generateMutation.mutate()}
          >
            {generateMutation.isPending ? <Loader2 className="animate-spin" /> : <Zap />}
            生成 ({engine === "local" ? "本地" : "云端"})
          </Button>
        </>
      }
      result={
        resultUrl ? (
          <div className="overflow-hidden rounded-xl border border-border bg-card p-2">
            <img src={resultUrl} alt="result" className="mx-auto max-h-[480px] rounded-lg object-contain" />
          </div>
        ) : (
          <div className="flex aspect-video items-center justify-center rounded-xl border border-dashed border-border text-sm text-muted-foreground">
            生成结果将显示在这里
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

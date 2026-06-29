import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Upload, Zap } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  angleGenerate,
  anglePoll,
  deleteHistory,
  fetchHistory,
  fetchModelScopeToken,
  fileToDataUrl,
  newClientId,
} from "./api";
import { HistoryMasonry } from "./components/HistoryMasonry";
import { ToolLayout } from "./components/ToolLayout";

const CLIENT_ID = newClientId();

export function AngleToolPage() {
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState("");
  const [dataUri, setDataUri] = useState("");
  const [azimuth, setAzimuth] = useState(0);
  const [elevation, setElevation] = useState(0);
  const [extraPrompt, setExtraPrompt] = useState("");
  const [resultUrl, setResultUrl] = useState("");

  const historyQuery = useQuery({ queryKey: ["history", "angle"], queryFn: () => fetchHistory("angle") });

  const buildPrompt = () => {
    const base = `camera azimuth ${azimuth}°, elevation ${elevation}°`;
    return extraPrompt.trim() ? `${extraPrompt.trim()}\n${base}` : base;
  };

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => fileToDataUrl(file),
    onSuccess: (uri, file) => {
      setDataUri(uri);
      setPreview(URL.createObjectURL(file));
      toast.success("图片已加载");
    },
  });

  const generateMutation = useMutation({
    mutationFn: async () => {
      if (!dataUri) throw new Error("请先上传图片");
      const token = await fetchModelScopeToken();
      const payload = {
        prompt: buildPrompt(),
        api_key: token,
        type: "angle",
        model: "Qwen/Qwen-Image-Edit-2511",
        image_urls: [dataUri],
        client_id: CLIENT_ID,
      };

      let result = await angleGenerate(payload);
      while (result.status === "timeout" && result.task_id) {
        const cont = window.confirm("云端生成超时，是否继续等待？");
        if (!cont) throw new Error("已取消等待");
        result = await anglePoll({
          task_id: result.task_id,
          api_key: token,
          client_id: CLIENT_ID,
        });
      }
      return result;
    },
    onSuccess: (data) => {
      const url = data.url ?? data.images?.[0];
      if (url) {
        setResultUrl(url);
        toast.success("视角生成完成");
        void queryClient.invalidateQueries({ queryKey: ["history", "angle"] });
      }
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "生成失败"),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteHistory,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["history", "angle"] }),
  });

  return (
    <ToolLayout
      title="角度控制"
      subtitle="基于 Qwen Image Edit 的相机视角重塑（云端）"
      testId="tool-angle"
      controls={
        <>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) uploadMutation.mutate(file);
              e.target.value = "";
            }}
          />
          <Button type="button" variant="outline" className="w-full" onClick={() => fileRef.current?.click()}>
            <Upload />
            上传原图
          </Button>
          {preview ? <img src={preview} alt="preview" className="rounded-lg border object-cover" /> : null}
          <div className="space-y-2">
            <Label>方位角 Azimuth ({azimuth}°)</Label>
            <Input
              type="range"
              min={-180}
              max={180}
              value={azimuth}
              onChange={(e) => setAzimuth(Number(e.target.value))}
            />
          </div>
          <div className="space-y-2">
            <Label>仰角 Elevation ({elevation}°)</Label>
            <Input
              type="range"
              min={-90}
              max={90}
              value={elevation}
              onChange={(e) => setElevation(Number(e.target.value))}
            />
          </div>
          <div className="space-y-2">
            <Label>附加提示词（可选）</Label>
            <Textarea rows={3} value={extraPrompt} onChange={(e) => setExtraPrompt(e.target.value)} />
          </div>
          <Button
            type="button"
            className="w-full"
            disabled={generateMutation.isPending}
            onClick={() => generateMutation.mutate()}
          >
            {generateMutation.isPending ? <Loader2 className="animate-spin" /> : <Zap />}
            生成新视角
          </Button>
        </>
      }
      result={
        resultUrl ? (
          <div className="grid gap-4 md:grid-cols-2">
            {preview ? <img src={preview} alt="before" className="rounded-xl border object-contain" /> : null}
            <img src={resultUrl} alt="after" className="rounded-xl border object-contain" />
          </div>
        ) : (
          <div className="flex aspect-video items-center justify-center rounded-xl border border-dashed text-sm text-muted-foreground">
            生成结果（3D 预览器待后续 parity 补全）
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

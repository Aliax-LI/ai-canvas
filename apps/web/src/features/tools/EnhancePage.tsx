import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Upload, Zap } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  alignMsSize,
  comfyGenerate,
  deleteHistory,
  fetchHistory,
  fetchModelScopeToken,
  msGenerate,
  newClientId,
  uploadComfyImages,
} from "./api";
import { HistoryMasonry } from "./components/HistoryMasonry";
import { ToolLayout } from "./components/ToolLayout";

const CLIENT_ID = newClientId();

export function EnhanceToolPage() {
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<"local" | "ms">("local");
  const [uploadedName, setUploadedName] = useState("");
  const [preview, setPreview] = useState("");
  const [strength, setStrength] = useState(0.8);
  const [msPrompt, setMsPrompt] = useState("masterpiece, best quality, ultra-detailed, high resolution");
  const [naturalSize, setNaturalSize] = useState({ w: 1024, h: 1024 });
  const [resultUrl, setResultUrl] = useState("");

  const historyQuery = useQuery({ queryKey: ["history", "enhance"], queryFn: () => fetchHistory("enhance") });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadComfyImages([file]),
    onSuccess: (names, file) => {
      if (!names[0]) throw new Error("上传失败");
      setUploadedName(names[0]);
      setPreview(URL.createObjectURL(file));
      const img = new Image();
      img.onload = () => setNaturalSize({ w: img.naturalWidth, h: img.naturalHeight });
      img.src = URL.createObjectURL(file);
      toast.success("图片已上传");
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "上传失败"),
  });

  const generateMutation = useMutation({
    mutationFn: async () => {
      if (!uploadedName && !preview) throw new Error("请先上传图片");
      if (mode === "ms") {
        const token = await fetchModelScopeToken();
        const size = alignMsSize(naturalSize.w, naturalSize.h);
        const data = await msGenerate({
          prompt: msPrompt,
          api_key: token,
          model: "black-forest-labs/FLUX.2-klein-9B",
          image_urls: [preview],
          width: size.width,
          height: size.height,
          loras: { "Daniel8152/Klein-enhance": strength },
          client_id: CLIENT_ID,
        });
        return { images: data.url ? [data.url] : data.images };
      }
      return comfyGenerate({
        workflow_json: "Z-Image-Enhance.json",
        params: { "15": { image: uploadedName }, "204": { value: strength } },
        type: "enhance",
        client_id: CLIENT_ID,
      });
    },
    onSuccess: (data) => {
      const url = data.images?.[0];
      if (url) {
        setResultUrl(url);
        toast.success("增强完成");
        void queryClient.invalidateQueries({ queryKey: ["history", "enhance"] });
      }
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "处理失败"),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteHistory,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["history", "enhance"] }),
  });

  return (
    <ToolLayout
      title="细节增强"
      subtitle="Z-Image Enhance 本地工作流或 ModelScope Klein LoRA"
      testId="tool-enhance"
      controls={
        <>
          <div className="flex gap-2 rounded-lg bg-muted p-1">
            {(["local", "ms"] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                className={`flex-1 rounded-md py-1.5 text-xs font-medium ${
                  mode === m ? "bg-background shadow-sm" : "text-muted-foreground"
                }`}
              >
                {m === "local" ? "本地 ComfyUI" : "ModelScope"}
              </button>
            ))}
          </div>
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
            上传图片
          </Button>
          {preview ? (
            <img src={preview} alt="preview" className="rounded-lg border object-cover" />
          ) : null}
          <div className="space-y-2">
            <Label>增强强度 ({strength.toFixed(2)})</Label>
            <Input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={strength}
              onChange={(e) => setStrength(Number(e.target.value))}
            />
          </div>
          {mode === "ms" ? (
            <div className="space-y-2">
              <Label>提示词</Label>
              <Input value={msPrompt} onChange={(e) => setMsPrompt(e.target.value)} />
            </div>
          ) : null}
          <Button
            type="button"
            className="w-full"
            disabled={generateMutation.isPending}
            onClick={() => generateMutation.mutate()}
          >
            {generateMutation.isPending ? <Loader2 className="animate-spin" /> : <Zap />}
            开始增强
          </Button>
        </>
      }
      result={
        resultUrl ? (
          <img src={resultUrl} alt="result" className="mx-auto max-h-[480px] rounded-xl border object-contain" />
        ) : (
          <div className="flex aspect-video items-center justify-center rounded-xl border border-dashed text-sm text-muted-foreground">
            增强结果
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

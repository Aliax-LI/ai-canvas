import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Upload, Zap } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  alignMsSize,
  comfyGenerate,
  deleteHistory,
  fetchHistory,
  fileToDataUrl,
  msGenerate,
  newClientId,
  uploadComfyImages,
} from "./api";
import { HistoryMasonry } from "./components/HistoryMasonry";
import { ToolLayout } from "./components/ToolLayout";

const CLIENT_ID = newClientId();

export function KleinToolPage() {
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<"local" | "cloud">("local");
  const [prompt, setPrompt] = useState("");
  const [uploadedNames, setUploadedNames] = useState<string[]>([]);
  const [dataUrls, setDataUrls] = useState<string[]>([]);
  const [preview, setPreview] = useState("");
  const [naturalSize, setNaturalSize] = useState({ w: 1024, h: 1024 });
  const [resultUrl, setResultUrl] = useState("");

  const historyQuery = useQuery({ queryKey: ["history", "klein"], queryFn: () => fetchHistory("klein") });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const names = await uploadComfyImages([file]);
      const dataUrl = await fileToDataUrl(file);
      return { names, dataUrl, file };
    },
    onSuccess: ({ names, dataUrl, file }) => {
      if (!names[0]) throw new Error("上传失败");
      setUploadedNames((prev) => [...prev, names[0]].slice(0, 3));
      setDataUrls((prev) => [...prev, dataUrl].slice(0, 3));
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
      if (!prompt.trim()) throw new Error("请输入提示词");
      if (mode === "cloud") {
        if (!dataUrls[0]) throw new Error("请上传主图");
        const size = alignMsSize(naturalSize.w, naturalSize.h);
        const data = await msGenerate({
          prompt: prompt.trim(),
          model: "black-forest-labs/FLUX.2-klein-9B",
          image_urls: dataUrls.filter(Boolean),
          width: size.width,
          height: size.height,
          client_id: CLIENT_ID,
        });
        return { images: data.url ? [data.url] : data.images };
      }
      if (!uploadedNames[0]) throw new Error("请上传主图");
      return comfyGenerate({
        prompt: prompt.trim(),
        workflow_json: "Flux2-Klein.json",
        type: "klein",
        params: {
          "168": { text: prompt.trim() },
          "158": { noise_seed: Math.floor(Math.random() * 1_000_000) },
          "278": { image: uploadedNames[0] },
          "270": { image: uploadedNames[1] ?? "" },
          "292": { image: uploadedNames[2] ?? "" },
          "313": { value: Boolean(uploadedNames[1]) },
          "314": { value: Boolean(uploadedNames[2]) },
        },
        client_id: CLIENT_ID,
      });
    },
    onSuccess: (data) => {
      const url = data.images?.[0];
      if (url) {
        setResultUrl(url);
        toast.success("编辑完成");
        void queryClient.invalidateQueries({ queryKey: ["history", "klein"] });
      }
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "生成失败"),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteHistory,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["history", "klein"] }),
  });

  return (
    <ToolLayout
      title="图片编辑"
      subtitle="FLUX.2 Klein 本地工作流或 ModelScope 云端"
      testId="tool-klein"
      controls={
        <>
          <div className="flex gap-2 rounded-lg bg-muted p-1">
            {(["local", "cloud"] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                className={`flex-1 rounded-md py-1.5 text-xs font-medium ${
                  mode === m ? "bg-background shadow-sm" : "text-muted-foreground"
                }`}
              >
                {m === "local" ? "本地" : "云端"}
              </button>
            ))}
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => {
              const files = [...(e.target.files ?? [])];
              for (const file of files.slice(0, 3)) uploadMutation.mutate(file);
              e.target.value = "";
            }}
          />
          <Button type="button" variant="outline" className="w-full" onClick={() => fileRef.current?.click()}>
            <Upload />
            上传参考图 ({uploadedNames.length}/3)
          </Button>
          {preview ? <img src={preview} alt="preview" className="rounded-lg border object-cover" /> : null}
          <div className="space-y-2">
            <Label>编辑提示词</Label>
            <Textarea rows={4} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
          </div>
          <Button
            type="button"
            className="w-full"
            disabled={generateMutation.isPending}
            onClick={() => generateMutation.mutate()}
          >
            {generateMutation.isPending ? <Loader2 className="animate-spin" /> : <Zap />}
            执行编辑
          </Button>
        </>
      }
      result={
        resultUrl ? (
          <img src={resultUrl} alt="result" className="mx-auto max-h-[480px] rounded-xl border object-contain" />
        ) : (
          <div className="flex aspect-video items-center justify-center rounded-xl border border-dashed text-sm text-muted-foreground">
            编辑结果
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

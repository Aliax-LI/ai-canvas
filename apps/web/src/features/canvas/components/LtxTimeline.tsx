import { useCallback, useMemo } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { mediaPreviewUrl } from "../api";
import {
  defaultLtxTextSegment,
  ltxParseTimeline,
  ltxSerializeTimeline,
  ltxSyncSecondsFromInputs,
  type LtxSegment,
} from "../lib/ltx";

interface LtxTimelineProps {
  nodeId: string;
  data: Record<string, unknown>;
  onUpdate: (patch: Record<string, unknown>) => void;
}

export function LtxTimeline({ nodeId, data, onUpdate }: LtxTimelineProps) {
  const timeline = useMemo(() => ltxParseTimeline({ id: nodeId, data } as never), [nodeId, data]);
  const segments = timeline.segments;
  const globalPrompt = String(data.globalPrompt ?? "");
  const durationSeconds = Number(data.durationSeconds ?? 5);
  const frameRate = Number(data.frameRate ?? 24);

  const writeTimeline = useCallback(
    (nextSegments: LtxSegment[]) => {
      const json = ltxSerializeTimeline({ segments: nextSegments, audioSegments: timeline.audioSegments });
      onUpdate({ ltxTimelineData: json, ltxSegments: nextSegments });
    },
    [onUpdate, timeline.audioSegments],
  );

  const updateSegment = useCallback(
    (segId: string, patch: Partial<LtxSegment>) => {
      writeTimeline(segments.map((s) => (s.id === segId ? { ...s, ...patch } : s)));
    },
    [segments, writeTimeline],
  );

  const addTextSegment = useCallback(() => {
    const lastEnd = segments.reduce(
      (m, s) => Math.max(m, (Number(s.start) || 0) + (Number(s.length) || 0)),
      0,
    );
    const seg = defaultLtxTextSegment(lastEnd, Math.max(6, frameRate));
    writeTimeline([...segments, seg]);
  }, [segments, frameRate, writeTimeline]);

  const removeSegment = useCallback(
    (segId: string) => {
      const seg = segments.find((s) => s.id === segId);
      if (!seg || seg.canvasSourceId) return;
      writeTimeline(segments.filter((s) => s.id !== segId));
    },
    [segments, writeTimeline],
  );

  return (
    <div className="space-y-2" data-testid={`canvas-ltx-timeline-${nodeId}`}>
      <div>
        <Label className="text-xs text-muted-foreground">全局提示词</Label>
        <Textarea
          value={globalPrompt}
          onChange={(e) => onUpdate({ globalPrompt: e.target.value })}
          className="min-h-[48px] text-xs"
          placeholder="LTX 全局 prompt"
        />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <Label className="text-xs text-muted-foreground">时长 (秒)</Label>
          <Input
            type="number"
            step="0.1"
            min={0.1}
            value={durationSeconds}
            className="h-7 text-xs"
            onChange={(e) => {
              const patch = ltxSyncSecondsFromInputs(data, "seconds", Number(e.target.value));
              onUpdate(patch);
            }}
          />
        </div>
        <div>
          <Label className="text-xs text-muted-foreground">帧率</Label>
          <Input
            type="number"
            min={1}
            max={240}
            value={frameRate}
            className="h-7 text-xs"
            onChange={(e) => {
              const patch = ltxSyncSecondsFromInputs(data, "rate", Number(e.target.value));
              onUpdate(patch);
            }}
          />
        </div>
      </div>

      <div className="flex items-center justify-between">
        <Label className="text-xs text-muted-foreground">时间轴片段 ({segments.length})</Label>
        <Button type="button" size="sm" variant="outline" className="h-6 px-2 text-xs" onClick={addTextSegment}>
          <Plus className="mr-1 size-3" />
          文本段
        </Button>
      </div>

      <div className="max-h-[200px] space-y-1.5 overflow-y-auto">
        {segments.length === 0 ? (
          <p className="text-xs text-muted-foreground">连接图片节点或添加文本段</p>
        ) : (
          segments.map((seg) => (
            <div
              key={seg.id}
              className="rounded border border-border bg-muted/20 p-2 text-xs"
              data-testid={`canvas-ltx-seg-${seg.id}`}
            >
              <div className="mb-1 flex items-center justify-between gap-1">
                <span className="font-medium capitalize text-muted-foreground">
                  {seg.type}
                  {seg.canvasSourceId ? " · 连线" : ""}
                </span>
                {!seg.canvasSourceId ? (
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="size-6"
                    onClick={() => removeSegment(seg.id)}
                  >
                    <Trash2 className="size-3" />
                  </Button>
                ) : null}
              </div>
              <div className="grid grid-cols-2 gap-1.5">
                <div>
                  <Label className="text-[10px] text-muted-foreground">起始帧</Label>
                  <Input
                    type="number"
                    min={0}
                    value={Number(seg.start) || 0}
                    readOnly={Boolean(seg.canvasSourceId)}
                    className="h-6 text-xs"
                    onChange={(e) => updateSegment(seg.id, { start: Number(e.target.value) || 0 })}
                  />
                </div>
                <div>
                  <Label className="text-[10px] text-muted-foreground">长度</Label>
                  <Input
                    type="number"
                    min={1}
                    value={Number(seg.length) || 1}
                    className="h-6 text-xs"
                    onChange={(e) => updateSegment(seg.id, { length: Math.max(1, Number(e.target.value) || 1) })}
                  />
                </div>
              </div>
              {seg.type === "image" && seg.imageB64 ? (
                <img
                  src={mediaPreviewUrl(String(seg.imageB64), 80)}
                  alt=""
                  className="mt-1 h-10 w-full rounded object-cover"
                />
              ) : null}
              <Textarea
                value={String(seg.prompt ?? "")}
                onChange={(e) => updateSegment(seg.id, { prompt: e.target.value })}
                className="mt-1 min-h-[36px] text-xs"
                placeholder="片段 prompt"
              />
            </div>
          ))
        )}
      </div>
    </div>
  );
}

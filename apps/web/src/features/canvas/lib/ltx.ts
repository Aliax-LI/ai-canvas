import type { Edge, Node } from "@xyflow/react";
import {
  imageRefsOnly,
  orderedSources,
  type GeneratorSource,
} from "./graph";

export const LTX_DIRECTOR_WORKFLOW = "LTXDirectorv2-API.json";
export const LTX_DIRECTOR_WF_NODE = "46";
export const LTX_DIRECTOR_SEED_NODE = "94:28";

export interface LtxSegment {
  id: string;
  type: "text" | "image";
  prompt?: string;
  start: number;
  length: number;
  imageB64?: string;
  imageFile?: string | null;
  canvasSourceId?: string;
  guideStrength?: number;
  color?: string;
}

export interface LtxTimeline {
  segments: LtxSegment[];
  audioSegments?: unknown[];
}

function nodeData(node: Node): Record<string, unknown> {
  return (node.data ?? {}) as Record<string, unknown>;
}

export function ltxParseTimeline(node: Node): LtxTimeline {
  const raw = String(nodeData(node).ltxTimelineData ?? "");
  if (!raw) {
    const legacy = Array.isArray(nodeData(node).ltxSegments)
      ? (nodeData(node).ltxSegments as LtxSegment[])
      : [];
    return { segments: legacy, audioSegments: [] };
  }
  try {
    const parsed = JSON.parse(raw) as LtxTimeline;
    return {
      segments: Array.isArray(parsed.segments) ? parsed.segments : [],
      audioSegments: parsed.audioSegments ?? [],
    };
  } catch {
    return { segments: [], audioSegments: [] };
  }
}

export function ltxSerializeTimeline(timeline: LtxTimeline): string {
  return JSON.stringify(timeline);
}

export function ltxDirectorSyncSeconds(data: Record<string, unknown>): {
  durationSeconds: number;
  durationFrames: number;
} {
  const frameRate = Math.max(1, Number(data.frameRate) || 24);
  const durationFrames = Math.max(1, Number(data.durationFrames) || 120);
  const durationSeconds = Math.round((durationFrames / frameRate) * 1000) / 1000;
  return { durationSeconds, durationFrames };
}

export function ltxSyncSecondsFromInputs(
  data: Record<string, unknown>,
  field: "seconds" | "frames" | "rate",
  value: number,
): Record<string, unknown> {
  const frameRate = Math.max(1, Number(data.frameRate) || 24);
  if (field === "seconds") {
    const durationSeconds = Math.max(0.1, Math.min(1000, value));
    const durationFrames = Math.max(1, Math.round(durationSeconds * frameRate));
    return { durationSeconds, durationFrames, frameRate };
  }
  if (field === "frames") {
    const durationFrames = Math.max(1, Math.min(10000, Math.round(value)));
    const durationSeconds = Math.round((durationFrames / frameRate) * 1000) / 1000;
    return { durationSeconds, durationFrames, frameRate };
  }
  const nextRate = Math.max(1, Math.min(240, Math.round(value)));
  const durationFrames = Math.max(1, Number(data.durationFrames) || 120);
  const durationSeconds = Math.round((durationFrames / nextRate) * 1000) / 1000;
  return { durationSeconds, durationFrames, frameRate: nextRate };
}

function newSegmentId(): string {
  return `ltxseg_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
}

export function defaultLtxTextSegment(start = 0, length = 24): LtxSegment {
  return {
    id: newSegmentId(),
    type: "text",
    prompt: "",
    start,
    length: Math.max(1, length),
    guideStrength: 1,
  };
}

/** 对齐上游 ltxSyncConnectedImagesToTimeline */
export function ltxSyncConnectedImagesToTimeline(
  node: Node,
  nodes: Node[],
  edges: Edge[],
): { timeline: LtxTimeline; patch: Record<string, unknown> } {
  const data = nodeData(node);
  const hadTimeline = Boolean(data.ltxTimelineData);
  const sources = orderedSources(node.id, data, nodes, edges);
  const imageInputs = sources.filter((src) => imageRefsOnly(src.refs ?? []).length > 0);
  const timeline = ltxParseTimeline(node);
  const fps = Math.max(1, Number(data.frameRate) || 24);
  const defaultLen = Math.max(6, fps);
  const manual = (timeline.segments || []).filter((s) => !s.canvasSourceId);
  const existingAuto = new Map(
    (timeline.segments || [])
      .filter((s) => s.canvasSourceId)
      .map((s) => [s.canvasSourceId as string, s]),
  );
  const autoSegs: LtxSegment[] = [];
  let cursor = 0;

  for (const src of imageInputs) {
    const ref = imageRefsOnly(src.refs ?? [])[0];
    const url = ref?.url;
    if (!url) continue;
    let seg = existingAuto.get(src.id);
    if (seg) {
      if (seg.imageB64 !== url) {
        seg = { ...seg, imageB64: url, imageFile: null };
      }
      if (!seg.length || seg.length < 1) seg = { ...seg, length: defaultLen };
    } else {
      seg = {
        id: newSegmentId(),
        start: cursor,
        length: defaultLen,
        prompt: src.prompt || "",
        type: "image",
        imageB64: url,
        canvasSourceId: src.id,
        guideStrength: 1,
      };
    }
    seg.start = cursor;
    cursor += Math.max(1, Number(seg.length) || defaultLen);
    autoSegs.push(seg);
  }

  let nextStart = cursor;
  const reflowedManual = [...manual].sort(
    (a, b) => (Number(a.start) || 0) - (Number(b.start) || 0),
  );
  for (const seg of reflowedManual) {
    seg.start = nextStart;
    nextStart += Math.max(1, Number(seg.length) || defaultLen);
  }

  const allSegs = [...autoSegs, ...reflowedManual];
  const maxEnd = allSegs.reduce(
    (m, s) => Math.max(m, (Number(s.start) || 0) + (Number(s.length) || 0)),
    0,
  );

  const patch: Record<string, unknown> = {};
  if (maxEnd > (Number(data.durationFrames) || 0)) {
    patch.durationFrames = Math.ceil(maxEnd);
    const synced = ltxDirectorSyncSeconds({ ...data, durationFrames: patch.durationFrames });
    patch.durationSeconds = synced.durationSeconds;
  }

  const nextTimeline: LtxTimeline = {
    segments: allSegs,
    audioSegments: timeline.audioSegments ?? [],
  };
  const timelineJson = ltxSerializeTimeline(nextTimeline);

  if (!hadTimeline && allSegs.length === 0) {
    return { timeline: nextTimeline, patch: {} };
  }

  if (hadTimeline && data.ltxTimelineData === timelineJson && !patch.durationFrames) {
    return { timeline: nextTimeline, patch: {} };
  }

  patch.ltxTimelineData = timelineJson;
  patch.ltxSegments = allSegs;

  return { timeline: nextTimeline, patch };
}

export function ltxBuildContiguousRelay(
  node: Node,
  globalPromptFallback = "",
): {
  local_prompts: string;
  segment_lengths: string;
  guide_strength: string;
  sortedSegments: LtxSegment[];
} {
  const data = nodeData(node);
  const durationFrames = Math.max(1, Number(data.durationFrames) || 120);
  const fallback = (globalPromptFallback || String(data.globalPrompt ?? "")).trim() || ".";
  const timeline = ltxParseTimeline(node);
  const sortedSegments = [...timeline.segments].sort(
    (a, b) => (Number(a.start) || 0) - (Number(b.start) || 0),
  );
  const contiguousLengths: number[] = [];
  const contiguousPrompts: string[] = [];
  let currentCursor = 0;
  let pendingGap = 0;

  for (const seg of sortedSegments) {
    const start = Number(seg.start) || 0;
    const length = Math.max(1, Number(seg.length) || 1);
    if (start >= durationFrames) break;
    if (start > currentCursor) {
      const gapLength = Math.min(start, durationFrames) - currentCursor;
      if (contiguousLengths.length > 0) contiguousLengths[contiguousLengths.length - 1] += gapLength;
      else pendingGap += gapLength;
    }
    const clippedEnd = Math.min(start + length, durationFrames);
    const clippedLength = clippedEnd - start;
    contiguousLengths.push(clippedLength + pendingGap);
    const prompt = (seg.prompt || "").trim();
    contiguousPrompts.push(prompt || fallback);
    if (!prompt) seg.prompt = fallback;
    pendingGap = 0;
    currentCursor = start + length;
  }

  const clampedCursor = Math.min(currentCursor, durationFrames);
  if (contiguousLengths.length > 0 && clampedCursor < durationFrames) {
    contiguousLengths[contiguousLengths.length - 1] += durationFrames - clampedCursor;
  }
  if (!contiguousLengths.length) {
    contiguousLengths.push(durationFrames);
    contiguousPrompts.push(fallback);
  }

  const guideStrength = sortedSegments
    .filter((s) => s.type !== "text")
    .map((s) => (s.guideStrength !== undefined ? s.guideStrength : 1.0).toFixed(2))
    .join(",");

  return {
    local_prompts: contiguousPrompts.join(" | "),
    segment_lengths: contiguousLengths.join(","),
    guide_strength: guideStrength,
    sortedSegments,
  };
}

export interface LtxDirectorInputs {
  global_prompt: string;
  duration_frames: number;
  duration_seconds: number;
  timeline_data: string;
  local_prompts: string;
  segment_lengths: string;
  guide_strength: string;
  epsilon: number;
  frame_rate: number;
  use_custom_audio: boolean;
  display_mode: string;
  custom_width: number;
  custom_height: number;
  resize_method: string;
  divisible_by: number;
  img_compression: number;
  timeline_ui: string;
}

export function ltxDirectorBuildTimelinePayload(
  node: Node,
  globalPromptFallback = "",
): LtxDirectorInputs {
  const data = nodeData(node);
  const relay = ltxBuildContiguousRelay(node, globalPromptFallback);
  const timeline = ltxParseTimeline(node);
  const timelineJson = ltxSerializeTimeline({
    segments: relay.sortedSegments,
    audioSegments: timeline.audioSegments ?? [],
  });

  return {
    global_prompt: (globalPromptFallback || String(data.globalPrompt ?? "")).trim(),
    duration_frames: Number(data.durationFrames) || 120,
    duration_seconds: Number(data.durationSeconds) || 5,
    timeline_data: timelineJson,
    local_prompts: relay.local_prompts,
    segment_lengths: relay.segment_lengths,
    guide_strength: relay.guide_strength,
    epsilon: Number(data.epsilon) || 0.001,
    frame_rate: Number(data.frameRate) || 24,
    use_custom_audio: Boolean(data.useCustomAudio),
    display_mode: String(data.displayMode ?? "seconds"),
    custom_width: Math.max(0, Number(data.customWidth) || 0),
    custom_height: Math.max(0, Number(data.customHeight) || 0),
    resize_method: "maintain aspect ratio",
    divisible_by: Math.max(1, Number(data.divisibleBy) || 32),
    img_compression: Number(data.imgCompression) ?? 18,
    timeline_ui: "",
  };
}

export function ltxTimelineSegments(node: Node): LtxSegment[] {
  return ltxParseTimeline(node).segments;
}

export function ltxHasRunnableContent(
  node: Node,
  sources: GeneratorSource[],
  globalPrompt: string,
): boolean {
  const segments = ltxTimelineSegments(node);
  const hasSegPrompt = segments.some((s) => (s.prompt || "").trim());
  const hasImageSeg = segments.some((s) => s.type === "image" && (s.imageFile || s.imageB64));
  return Boolean(globalPrompt.trim()) || hasSegPrompt || hasImageSeg || sources.some((s) => s.prompt);
}

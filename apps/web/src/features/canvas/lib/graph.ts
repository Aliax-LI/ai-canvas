import type { Edge, Node } from "@xyflow/react";

export const CANVAS_GENERATOR_TYPES = [
  "generator",
  "msgen",
  "comfy",
  "ltxDirector",
  "video",
  "rh",
] as const;

export type CanvasGeneratorType = (typeof CANVAS_GENERATOR_TYPES)[number];

export const CANVAS_MEDIA_OUTPUT_TYPES = [
  "generator",
  "msgen",
  "comfy",
  "ltxDirector",
  "video",
  "rh",
] as const;

const REF_IMAGE_MAX = 8;

export interface MediaRef {
  url: string;
  name?: string;
  role?: string;
  kind?: string;
  nodeId?: string;
  outputIndex?: number;
}

export interface GeneratorSource {
  id: string;
  type: string;
  label: string;
  preview?: string;
  refs: MediaRef[];
  prompt: string;
  groupId?: string;
  imageId?: string;
}

export interface RunPayload {
  prompt: string;
  referenceImages: MediaRef[];
  sources: GeneratorSource[];
}

export interface LoopContext {
  index: number;
  total: number;
}

function nodeType(node: Node): string {
  return String(node.data?.nodeType ?? node.type ?? "");
}

function nodeData(node: Node): Record<string, unknown> {
  return (node.data ?? {}) as Record<string, unknown>;
}

function findNode(nodes: Node[], id: string): Node | undefined {
  return nodes.find((n) => n.id === id);
}

function incomingNodes(genId: string, nodes: Node[], edges: Edge[]): Node[] {
  return edges
    .filter((e) => e.target === genId)
    .map((e) => findNode(nodes, e.source))
    .filter((n): n is Node => Boolean(n));
}

export function outputUrlValue(item: unknown): string {
  if (typeof item === "string") return item;
  if (item && typeof item === "object" && "url" in item) {
    return String((item as { url?: string }).url ?? "");
  }
  return "";
}

function isVideoUrl(url: string): boolean {
  const clean = url.split("?")[0].toLowerCase();
  return /\.(mp4|webm|mov|m4v|avi|mkv|flv)$/.test(clean);
}

function isAudioUrl(url: string): boolean {
  const clean = url.split("?")[0].toLowerCase();
  return /\.(mp3|wav|ogg|m4a|aac|flac)$/.test(clean);
}

function mediaKindForNode(node: Node): string {
  const kind = String(nodeData(node).mediaKind ?? "");
  if (kind) return kind;
  const url = String(nodeData(node).url ?? "");
  if (isVideoUrl(url)) return "video";
  if (isAudioUrl(url)) return "audio";
  return "image";
}

function mediaKindForOutputItem(item: unknown): string {
  if (item && typeof item === "object") {
    const obj = item as Record<string, unknown>;
    const explicit = String(obj.kind ?? obj.mediaKind ?? "").toLowerCase();
    if (["image", "video", "audio", "text", "file"].includes(explicit)) return explicit;
  }
  const url = outputUrlValue(item);
  if (isVideoUrl(url)) return "video";
  if (isAudioUrl(url)) return "audio";
  return "image";
}

export function imageRefsOnly(refs: MediaRef[]): MediaRef[] {
  return refs
    .filter((ref) => ref?.url && (ref.kind ?? "image") === "image")
    .slice(0, REF_IMAGE_MAX);
}

function generatedImageRefs(node: Node): MediaRef[] {
  const type = nodeType(node);
  const keepGeneratedMedia = ["rh", "ltxDirector", "video"].includes(type);
  const outputs = Array.isArray(nodeData(node).generatedOutputs)
    ? (nodeData(node).generatedOutputs as unknown[])
    : [];
  const refs: MediaRef[] = [];
  for (let i = outputs.length - 1; i >= 0; i--) {
    const item = outputs[i];
    const url = outputUrlValue(item);
    if (!url) continue;
    const kind = mediaKindForOutputItem(item);
    if (!keepGeneratedMedia && kind !== "image") continue;
    refs.unshift({ url, name: `generated-${i + 1}`, kind });
  }
  return refs;
}

function mediaRefsFromNode(node: Node, nodes: Node[]): MediaRef[] {
  const type = nodeType(node);
  const data = nodeData(node);

  if (type === "image" && data.url) {
    const kind = mediaKindForNode(node);
    return [
      {
        url: String(data.url),
        name: String(data.name ?? kind),
        role: String(data.role ?? ""),
        kind,
      },
    ];
  }

  if (type === "group") {
    const items = Array.isArray(data.items) ? (data.items as string[]) : [];
    return items
      .map((id) => findNode(nodes, id))
      .filter((x): x is Node => Boolean(x))
      .filter((x) => nodeType(x) === "image" && nodeData(x).url)
      .map((item) => ({
        url: String(nodeData(item).url),
        name: String(nodeData(item).name ?? mediaKindForNode(item)),
        role: String(nodeData(item).role ?? ""),
        kind: mediaKindForNode(item),
      }));
  }

  if (type === "output") {
    const images = Array.isArray(data.images) ? data.images : [];
    const refs: MediaRef[] = [];
    for (let i = 0; i < images.length; i++) {
      const url = outputUrlValue(images[i]);
      if (!url) continue;
      refs.push({
        url,
        name: `output-${i + 1}`,
        kind: mediaKindForOutputItem(images[i]),
        nodeId: node.id,
        outputIndex: i,
      });
    }
    return refs;
  }

  if ((CANVAS_MEDIA_OUTPUT_TYPES as readonly string[]).includes(type)) {
    return generatedImageRefs(node);
  }

  return [];
}

function loopCount(node: Node): number {
  return Math.max(1, Math.min(100, Number(nodeData(node).count ?? 1) || 1));
}

function loopInputPromptItems(loopNode: Node, nodes: Node[], edges: Edge[]): string[] {
  if (!nodeData(loopNode).showPrompt) return [];
  const items: string[] = [];

  for (const src of incomingNodes(loopNode.id, nodes, edges)) {
    const type = nodeType(src);
    if (type === "prompt") {
      const text = String(nodeData(src).text ?? "").trim();
      if (text) items.push(text);
      continue;
    }
    if (type === "promptGroup") {
      const pgItems = Array.isArray(nodeData(src).items) ? (nodeData(src).items as string[]) : [];
      for (const pid of pgItems) {
        const p = findNode(nodes, pid);
        const text = p ? String(nodeData(p).text ?? "").trim() : "";
        if (text) items.push(text);
      }
      continue;
    }
    if (type === "loop") {
      const text = renderLoopPrompt(src, nodes, edges, { index: 1, total: loopCount(src) });
      if (text.trim()) items.push(text.trim());
      continue;
    }
    if (type === "llm") {
      const text = String(nodeData(src).outputText ?? "").trim();
      if (text) items.push(text);
    }
  }

  return items;
}

function loopInputPrompt(
  loopNode: Node,
  nodes: Node[],
  edges: Edge[],
  ctx: LoopContext,
): string {
  const items = loopInputPromptItems(loopNode, nodes, edges);
  if (!items.length) return "";
  const startBase = Math.max(1, Number(nodeData(loopNode).loopStart ?? 1) || 1);
  const currentIndex = Math.max(1, Number(ctx.index || startBase) || startBase);
  return items[(currentIndex - 1) % items.length] ?? "";
}

export function renderLoopPrompt(
  loopNode: Node,
  nodes: Node[],
  edges: Edge[],
  ctx: LoopContext = { index: 1, total: loopCount(loopNode) },
): string {
  if (!nodeData(loopNode).showPrompt) return "";
  const variable = String(nodeData(loopNode).variablePrompt ?? "").trim();
  const count = loopCount(loopNode);
  const index = Math.max(1, Number(ctx.index || 1) || 1);
  const total = Math.max(1, Number(ctx.total || count) || count);

  const replaceVars = (text: string) =>
    String(text || "")
      .replaceAll("《计数》", String(index))
      .replaceAll("《总数》", String(total))
      .replaceAll("《进度》", `${index}/${total}`)
      .replaceAll("[计数]", String(index))
      .replaceAll("[总数]", String(total))
      .replaceAll("[进度]", `${index}/${total}`);

  const selected = loopInputPrompt(loopNode, nodes, edges, ctx);
  if (selected) return replaceVars(selected);
  return replaceVars(variable);
}

function loopInputImageRefs(
  loopNode: Node,
  nodes: Node[],
  edges: Edge[],
  ctx: LoopContext,
): MediaRef[] {
  if (!nodeData(loopNode).imageInput) return [];
  const allRefs = incomingNodes(loopNode.id, nodes, edges).flatMap((n) =>
    mediaRefsFromNode(n, nodes).filter((ref) => ref.kind === "image" || !ref.kind),
  );
  if (!allRefs.length) return [];
  const startBase = Math.max(1, Number(nodeData(loopNode).loopStart ?? 1) || 1);
  const batchSize = Math.max(1, Math.min(100, Number(nodeData(loopNode).imageBatchSize ?? 1) || 1));
  const currentIndex = Math.max(1, Number(ctx.index || startBase) || startBase);
  const offset = currentIndex - startBase;
  const start = offset * batchSize;
  return allRefs.slice(start, start + batchSize);
}

function sourceFromNode(
  n: Node,
  nodes: Node[],
  edges: Edge[],
  loopCtx?: LoopContext,
): GeneratorSource[] | GeneratorSource | null {
  const type = nodeType(n);
  const data = nodeData(n);

  if (type === "output") {
    const images = Array.isArray(data.images) ? data.images : [];
    const reversed = [...images].map((item, index) => ({ item, index })).reverse();
    const found = reversed.find((entry) => outputUrlValue(entry.item));
    if (found) {
      const last = outputUrlValue(found.item);
      const kind = mediaKindForOutputItem(found.item);
      return {
        id: n.id,
        type: "outputImage",
        label: "上游输出",
        preview: last,
        refs: [{ url: last, name: "output.png", kind, nodeId: n.id, outputIndex: found.index }],
        prompt: "",
      };
    }
    return null;
  }

  if ((CANVAS_MEDIA_OUTPUT_TYPES as readonly string[]).includes(type)) {
    const refs = generatedImageRefs(n);
    if (refs.length) {
      return refs.map((ref, i) => ({
        id: `${n.id}:generated:${i}:${ref.url}`,
        type: "generatedImage",
        label: `上游生成 ${i + 1}`,
        preview: ref.url,
        refs: [ref],
        prompt: "",
      }));
    }
    return null;
  }

  if (type === "image" && data.url) {
    const kind = mediaKindForNode(n);
    return {
      id: n.id,
      type: kind,
      label: String(data.name ?? kind),
      preview: String(data.url),
      refs: [
        {
          url: String(data.url),
          name: String(data.name ?? kind),
          role: String(data.role ?? ""),
          kind,
        },
      ],
      prompt: "",
    };
  }

  if (type === "group") {
    const itemIds = Array.isArray(data.items) ? (data.items as string[]) : [];
    const items = itemIds.map((id) => findNode(nodes, id)).filter((x): x is Node => Boolean(x));
    const sources: GeneratorSource[] = [];

    for (const img of items.filter((x) => nodeType(x) === "image" && nodeData(x).url)) {
      const kind = mediaKindForNode(img);
      sources.push({
        id: `${n.id}:${img.id}`,
        type: `group-${kind}`,
        groupId: n.id,
        imageId: img.id,
        label: String(nodeData(img).name ?? kind),
        preview: String(nodeData(img).url),
        refs: [
          {
            url: String(nodeData(img).url),
            name: String(nodeData(img).name ?? kind),
            role: String(nodeData(img).role ?? ""),
            kind,
          },
        ],
        prompt: "",
      });
    }

    const prompts = items
      .filter((x) => nodeType(x) === "prompt")
      .map((p) => String(nodeData(p).text ?? "").trim())
      .filter(Boolean);
    if (prompts.length) {
      const combined = prompts.join("\n\n");
      sources.push({
        id: `${n.id}:prompts`,
        type: "groupPrompt",
        groupId: n.id,
        label: combined.slice(0, 32),
        refs: [],
        prompt: combined,
      });
    }
    return sources.length ? sources : null;
  }

  if (type === "prompt") {
    return {
      id: n.id,
      type: "prompt",
      label: String(data.text ?? "提示词").slice(0, 32),
      refs: [],
      prompt: String(data.text ?? ""),
    };
  }

  if (type === "loop") {
    const ctx = loopCtx ?? { index: 1, total: loopCount(n) };
    const prompt = renderLoopPrompt(n, nodes, edges, ctx);
    const imageRefs = loopInputImageRefs(n, nodes, edges, ctx);
    const out: GeneratorSource[] = [];
    if (imageRefs.length) {
      const currentIndex = Math.max(1, Number(ctx.index || nodeData(n).loopStart || 1) || 1);
      imageRefs.forEach((ref, i) => {
        out.push({
          id: `${n.id}:image:${currentIndex + i}:${ref.url}`,
          type: "loopImage",
          label: `循环图 ${currentIndex + i}`,
          preview: ref.url,
          refs: [ref],
          prompt: i === 0 && !out.length ? prompt : "",
        });
      });
    }
    if (out.length) return out;
    return {
      id: n.id,
      type: "loop",
      label: `循环 ${loopCount(n)}x`,
      refs: [],
      prompt,
    };
  }

  if (type === "promptGroup") {
    const pgItems = Array.isArray(data.items) ? (data.items as string[]) : [];
    const prompts = pgItems
      .map((id) => findNode(nodes, id))
      .filter((x): x is Node => Boolean(x))
      .map((p) => String(nodeData(p).text ?? "").trim())
      .filter(Boolean);
    return {
      id: n.id,
      type: "promptGroup",
      label: `提示词 ${prompts.length} 个`,
      refs: [],
      prompt: prompts.join("\n\n"),
    };
  }

  if (type === "llm" && String(data.mode ?? "node") === "node" && data.outputText) {
    return {
      id: n.id,
      type: "llm",
      label: String(data.outputText ?? "LLM").slice(0, 32),
      refs: [],
      prompt: String(data.outputText ?? ""),
    };
  }

  return null;
}

export function generatorSources(
  genId: string,
  nodes: Node[],
  edges: Edge[],
  loopCtx?: LoopContext,
): GeneratorSource[] {
  return incomingNodes(genId, nodes, edges)
    .map((n) => sourceFromNode(n, nodes, edges, loopCtx))
    .flat()
    .filter((s): s is GeneratorSource => Boolean(s));
}

export function orderedSources(
  genId: string,
  genData: Record<string, unknown>,
  nodes: Node[],
  edges: Edge[],
  loopCtx?: LoopContext,
): GeneratorSource[] {
  const sources = generatorSources(genId, nodes, edges, loopCtx);
  let inputs = Array.isArray(genData.inputs) ? [...(genData.inputs as string[])] : [];
  inputs = inputs.filter((id) => sources.some((s) => s.id === id));
  for (const s of sources) {
    if (!inputs.includes(s.id)) inputs.push(s.id);
  }
  return inputs.map((id) => sources.find((s) => s.id === id)).filter((s): s is GeneratorSource => Boolean(s));
}

export function syncGeneratorInputs(
  genId: string,
  genData: Record<string, unknown>,
  nodes: Node[],
  edges: Edge[],
): string[] {
  const sources = generatorSources(genId, nodes, edges);
  let inputs = Array.isArray(genData.inputs) ? [...(genData.inputs as string[])] : [];
  inputs = inputs.filter((id) => sources.some((s) => s.id === id));
  for (const s of sources) {
    if (!inputs.includes(s.id)) inputs.push(s.id);
  }
  return inputs;
}

export function resolveRunPayload(
  genId: string,
  nodes: Node[],
  edges: Edge[],
  loopCtx?: LoopContext,
): RunPayload {
  const genNode = findNode(nodes, genId);
  const genData = genNode ? nodeData(genNode) : {};
  const sources = orderedSources(genId, genData, nodes, edges, loopCtx);
  const prompt = sources
    .map((s) => s.prompt)
    .filter(Boolean)
    .join("\n\n");
  const referenceImages = imageRefsOnly(sources.flatMap((s) => s.refs ?? []));
  return { prompt, referenceImages, sources };
}

export function findDownstreamOutput(
  genId: string,
  nodes: Node[],
  edges: Edge[],
): Node | undefined {
  return edges
    .filter((e) => e.source === genId)
    .map((e) => findNode(nodes, e.target))
    .find((n) => n && nodeType(n) === "output");
}

export function isGeneratorType(type: string | undefined): type is CanvasGeneratorType {
  return CANVAS_GENERATOR_TYPES.includes(type as CanvasGeneratorType);
}

export function needPromptOrImage(prompt: string, refs: MediaRef[]): boolean {
  return Boolean(prompt.trim()) || refs.length > 0;
}

export function defaultRunPrompt(prompt: string): string {
  return prompt.trim() || "Edit the reference images.";
}

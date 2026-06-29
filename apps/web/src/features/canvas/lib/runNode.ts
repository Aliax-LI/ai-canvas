import type { Edge, Node } from "@xyflow/react";
import {
  createCanvasComfyTask,
  createCanvasImageTask,
  createCanvasLlm,
  createCanvasVideo,
  msGenerate,
  newCanvasClientId,
  submitRunningHub,
  submitRunningHubWorkflow,
} from "../api";
import {
  defaultRunPrompt,
  findDownstreamOutput,
  needPromptOrImage,
  resolveRunPayload,
  type LoopContext,
} from "./graph";
import { waitForComfyTask, waitForImageTask, waitForRhTask } from "./nodeRun";
import { mergeGeneratedOutputs, type CanvasLogEntry } from "./runHelpers";

export interface RunNodeRuntime {
  nodes: Node[];
  edges: Edge[];
  getNodes: () => Node[];
  getEdges: () => Edge[];
  loopCtx?: LoopContext;
  cascadeTargetId?: string;
  updateNodeData: (nodeId: string, patch: Record<string, unknown>) => void;
  appendLog: (entry: Omit<CanvasLogEntry, "id" | "ts"> & { ts?: number }) => void;
  writeOutputImages: (outputNodeId: string, urls: string[]) => void;
}

function nodeData(node: Node): Record<string, unknown> {
  return (node.data ?? {}) as Record<string, unknown>;
}

function resolvePayload(nodeId: string, runtime: RunNodeRuntime) {
  return resolveRunPayload(nodeId, runtime.getNodes(), runtime.getEdges(), runtime.loopCtx);
}

function downstreamOutput(runtime: RunNodeRuntime, genId: string) {
  return findDownstreamOutput(genId, runtime.getNodes(), runtime.getEdges());
}

function writeUrls(runtime: RunNodeRuntime, genId: string, urls: string[], kind = "image") {
  if (!urls.length) return;
  const node = runtime.getNodes().find((n) => n.id === genId);
  const existing = node ? (nodeData(node).generatedOutputs as unknown[] | undefined) : undefined;
  runtime.updateNodeData(genId, {
    generatedOutputs: mergeGeneratedOutputs(existing, urls, kind),
  });
  const outNode = downstreamOutput(runtime, genId);
  if (outNode) runtime.writeOutputImages(outNode.id, urls);
}

export async function runGeneratorNode(node: Node, runtime: RunNodeRuntime): Promise<void> {
  const id = node.id;
  const data = nodeData(node);
  const { prompt, referenceImages } = resolvePayload(id, runtime);
  if (!needPromptOrImage(prompt, referenceImages)) {
    throw new Error("请连接提示词或参考图");
  }

  runtime.updateNodeData(id, { running: true, runStatus: "running", runError: "" });
  runtime.appendLog({ nodeId: id, nodeType: "generator", status: "running", message: "开始生成" });

  const effectivePrompt = defaultRunPrompt(prompt);
  const task = await createCanvasImageTask({
    prompt: effectivePrompt,
    provider_id: String(data.apiProvider ?? "comfly"),
    model: String(data.model ?? "dall-e-3"),
    size: String(data.resolution ?? "1k") === "1k" ? "1024x1024" : "512x512",
    reference_images: referenceImages.map((r) => ({ url: r.url, name: r.name })),
  });
  const images = await waitForImageTask(task.task_id);
  writeUrls(runtime, id, images);
  runtime.updateNodeData(id, { running: false, runStatus: "succeeded" });
  runtime.appendLog({
    nodeId: id,
    nodeType: "generator",
    status: "succeeded",
    message: `生成 ${images.length} 张图`,
  });
}

export async function runMsGenNode(node: Node, runtime: RunNodeRuntime): Promise<void> {
  const id = node.id;
  const data = nodeData(node);
  const { prompt, referenceImages } = resolvePayload(id, runtime);
  if (!needPromptOrImage(prompt, referenceImages)) {
    throw new Error("请连接提示词或参考图");
  }

  runtime.updateNodeData(id, { running: true, runStatus: "running", runError: "" });
  runtime.appendLog({ nodeId: id, nodeType: "msgen", status: "running" });

  const effectivePrompt = defaultRunPrompt(prompt);
  const imageUrls = referenceImages.map((r) => r.url);
  const modelKey = String(data.msgenModel ?? "zimage");
  const width = Number(data.msWidth ?? 1024);
  const height = Number(data.msHeight ?? 1024);
  const payload =
    modelKey === "zimage"
      ? {
          prompt: effectivePrompt,
          resolution: `${width}x${height}`,
          image_urls: imageUrls.length ? imageUrls : undefined,
          client_id: newCanvasClientId(),
        }
      : {
          prompt: effectivePrompt,
          model: String(data.msCustomModel ?? "Tongyi-MAI/Z-Image-Turbo"),
          width,
          height,
          size: `${width}x${height}`,
          image_urls: imageUrls.length ? imageUrls : undefined,
          client_id: newCanvasClientId(),
        };
  const result = await msGenerate(payload);
  const urls = result.url ? [result.url] : [];
  if (urls.length) writeUrls(runtime, id, urls);
  runtime.updateNodeData(id, { running: false, runStatus: "succeeded" });
  runtime.appendLog({ nodeId: id, nodeType: "msgen", status: "succeeded", message: "ModelScope 完成" });
}

export async function runComfyNode(node: Node, runtime: RunNodeRuntime): Promise<void> {
  const id = node.id;
  const data = nodeData(node);
  const { prompt, referenceImages } = resolvePayload(id, runtime);
  if (!needPromptOrImage(prompt, referenceImages)) {
    throw new Error("请连接提示词或参考图");
  }

  const mode = String(data.mode ?? "text");
  const width = Number(data.width ?? 1024);
  const height = Number(data.height ?? 1024);
  const workflow = String(data.comfyWorkflow ?? "");

  runtime.updateNodeData(id, { running: true, runStatus: "running", runError: "" });
  runtime.appendLog({ nodeId: id, nodeType: "comfy", status: "running", message: `模式 ${mode}` });

  const effectivePrompt = defaultRunPrompt(prompt);
  const workflowJson =
    mode === "custom" && workflow
      ? workflow
      : mode === "enhance"
        ? "enhance.json"
        : mode === "edit"
          ? "edit.json"
          : "Z-Image.json";

  const task = await createCanvasComfyTask({
    prompt: effectivePrompt,
    width,
    height,
    workflow_json: workflowJson,
    type: mode === "text" ? "zimage" : mode,
    params: { mode, ...(data.comfyParams as Record<string, unknown> | undefined) },
    client_id: newCanvasClientId(),
  });
  const result = await waitForComfyTask(task.task_id);
  const images = result.images ?? [];
  if (images.length) writeUrls(runtime, id, images);
  runtime.updateNodeData(id, { running: false, runStatus: "succeeded" });
  runtime.appendLog({ nodeId: id, nodeType: "comfy", status: "succeeded", message: "ComfyUI 完成" });
}

export async function runVideoNode(node: Node, runtime: RunNodeRuntime): Promise<void> {
  const id = node.id;
  const data = nodeData(node);
  const { prompt, referenceImages } = resolvePayload(id, runtime);
  if (!needPromptOrImage(prompt, referenceImages)) {
    throw new Error("请连接提示词或参考图");
  }

  runtime.updateNodeData(id, { running: true, runStatus: "running", runError: "" });
  runtime.appendLog({ nodeId: id, nodeType: "video", status: "running" });

  const effectivePrompt = defaultRunPrompt(prompt);
  const result = await createCanvasVideo({
    prompt: effectivePrompt,
    provider_id: String(data.apiProvider ?? "comfly"),
    model: String(data.model ?? "veo3-fast"),
    duration: Number(data.duration ?? 5),
    aspect_ratio: String(data.aspectRatio ?? "16:9"),
    enhance_prompt: Boolean(data.enhancePrompt),
    generate_audio: Boolean(data.generateAudio),
    multimodal: Boolean(data.multimodal),
  });
  const urls = result.urls ?? (result.url ? [result.url] : result.video ? [result.video] : []);
  if (urls.length) writeUrls(runtime, id, urls, "video");
  runtime.updateNodeData(id, { running: false, runStatus: "succeeded" });
  runtime.appendLog({ nodeId: id, nodeType: "video", status: "succeeded", message: "视频生成完成" });
}

export async function runLlmNode(node: Node, runtime: RunNodeRuntime): Promise<void> {
  const id = node.id;
  const data = nodeData(node);
  const { prompt } = resolvePayload(id, runtime);
  const message =
    prompt.trim() || String(data.chatInput ?? "").trim() || "Rewrite this into an image prompt";

  runtime.updateNodeData(id, { running: true, runStatus: "running", runError: "" });
  runtime.appendLog({ nodeId: id, nodeType: "llm", status: "running" });

  const result = await createCanvasLlm({
    message,
    system_prompt: String(data.systemPrompt ?? ""),
    model: String(data.model ?? ""),
    provider: String(data.llmProvider ?? "comfly"),
  });
  const text = result.text ?? "";
  runtime.updateNodeData(id, {
    running: false,
    runStatus: "succeeded",
    outputText: text,
  });
  runtime.appendLog({
    nodeId: id,
    nodeType: "llm",
    status: "succeeded",
    message: text ? text.slice(0, 48) : "LLM 已响应",
  });
}

export async function runRhNode(node: Node, runtime: RunNodeRuntime): Promise<void> {
  const id = node.id;
  const data = nodeData(node);
  const { prompt, referenceImages } = resolvePayload(id, runtime);
  if (!needPromptOrImage(prompt, referenceImages)) {
    throw new Error("请连接提示词或参考图");
  }

  const rhMode = String(data.rhMode ?? "app");
  const webappId = String(data.webappId ?? "");
  const workflowId = String(data.workflowId ?? "");
  const rhParams = (data.rhParams ?? {}) as Record<string, unknown>;

  runtime.updateNodeData(id, { running: true, runStatus: "running", runError: "" });
  runtime.appendLog({ nodeId: id, nodeType: "rh", status: "running" });

  const effectivePrompt = defaultRunPrompt(prompt);
  const nodeInfoList = [
    {
      prompt: effectivePrompt,
      images: referenceImages.map((r) => r.url),
      ...rhParams,
    },
  ];
  const submit =
    rhMode === "workflow"
      ? await submitRunningHubWorkflow({ workflowId, nodeInfoList })
      : await submitRunningHub({ webappId, nodeInfoList });
  if (!submit.taskId) throw new Error("未返回 taskId");
  const result = await waitForRhTask(submit.taskId);
  const urls = result.urls ?? [];
  if (urls.length) writeUrls(runtime, id, urls);
  runtime.updateNodeData(id, { running: false, runStatus: "succeeded" });
  runtime.appendLog({ nodeId: id, nodeType: "rh", status: "succeeded", message: "RunningHub 完成" });
}

export async function runLtxDirectorNode(_node: Node, _runtime: RunNodeRuntime): Promise<void> {
  throw new Error("LTX Director 完整运行待后续实现");
}

export async function runNodeByType(node: Node, runtime: RunNodeRuntime): Promise<void> {
  const type = String(node.data?.nodeType ?? node.type ?? "");
  switch (type) {
    case "generator":
      return runGeneratorNode(node, runtime);
    case "msgen":
      return runMsGenNode(node, runtime);
    case "comfy":
      return runComfyNode(node, runtime);
    case "video":
      return runVideoNode(node, runtime);
    case "llm":
      return runLlmNode(node, runtime);
    case "rh":
      return runRhNode(node, runtime);
    case "ltxDirector":
      return runLtxDirectorNode(node, runtime);
    default:
      throw new Error(`不支持运行节点类型: ${type}`);
  }
}

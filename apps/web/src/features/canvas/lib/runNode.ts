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
  uploadUrlToComfy,
} from "../api";
import {
  defaultRunPrompt,
  findDownstreamOutput,
  needPromptOrImage,
  resolveRunPayload,
  type LoopContext,
  type MediaRef,
} from "./graph";
import {
  LTX_DIRECTOR_SEED_NODE,
  LTX_DIRECTOR_WF_NODE,
  LTX_DIRECTOR_WORKFLOW,
  ltxDirectorBuildTimelinePayload,
  ltxHasRunnableContent,
  ltxTimelineSegments,
} from "./ltx";
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

async function comfyNameForRef(ref: MediaRef): Promise<string> {
  if (!ref.url) throw new Error("缺少输入图片");
  return uploadUrlToComfy(ref.url);
}

async function runComfyUpscale(imageUrl: string, resolution: number): Promise<string[]> {
  const inputName = await uploadUrlToComfy(imageUrl);
  const task = await createCanvasComfyTask({
    workflow_json: "upscale.json",
    params: {
      "15": { image: inputName },
      "172": { seed: Math.floor(Math.random() * 4294967295), resolution: Number(resolution || 2048) },
    },
    type: "upscale",
    client_id: newCanvasClientId(),
  });
  const result = await waitForComfyTask(task.task_id);
  return result.images ?? [];
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
  const ratio = String(data.ratio ?? "1:1");
  const resolution = String(data.resolution ?? "1k");
  const workflow = String(data.comfyWorkflow ?? "");
  const enhanceStrength = Number(data.enhanceStrength ?? 0.5);
  const enhanceUpscale = Boolean(data.enhanceUpscale);
  const enhanceUpscaleRes = Number(data.enhanceUpscaleRes ?? 2048);
  const editUpscale = Boolean(data.editUpscale);
  const editUpscaleRes = Number(data.editUpscaleRes ?? 2048);
  const editModel = String(data.editModel ?? "");

  runtime.updateNodeData(id, { running: true, runStatus: "running", runError: "" });
  runtime.appendLog({ nodeId: id, nodeType: "comfy", status: "running", message: `模式 ${mode}` });

  const effectivePrompt = defaultRunPrompt(prompt);
  let images: string[] = [];

  if (mode === "text") {
    const task = await createCanvasComfyTask({
      prompt: effectivePrompt,
      width,
      height,
      workflow_json: "Z-Image.json",
      type: "zimage",
      params: { mode, ratio, resolution, width, height },
      client_id: newCanvasClientId(),
    });
    const result = await waitForComfyTask(task.task_id);
    images = result.images ?? [];
  } else if (mode === "enhance") {
    if (!referenceImages.length) throw new Error("增强模式需要参考图");
    const inputName = await comfyNameForRef(referenceImages[0]);
    const task = await createCanvasComfyTask({
      workflow_json: "Z-Image-Enhance.json",
      params: {
        "15": { image: inputName },
        "204": { value: enhanceStrength },
        enhanceStrength,
        enhanceUpscale,
        enhanceUpscaleRes,
      },
      type: "enhance",
      client_id: newCanvasClientId(),
    });
    const result = await waitForComfyTask(task.task_id);
    const base = result.images ?? [];
    if (!base.length) throw new Error("ComfyUI 增强未返回图片");
    images = enhanceUpscale ? await runComfyUpscale(base[0], enhanceUpscaleRes) : base;
  } else if (mode === "edit") {
    if (!referenceImages.length) throw new Error("编辑模式需要参考图");
    const names: string[] = [];
    for (const ref of referenceImages.slice(0, 3)) {
      names.push(await comfyNameForRef(ref));
    }
    const task = await createCanvasComfyTask({
      prompt: effectivePrompt,
      workflow_json: "Flux2-Klein.json",
      type: "klein",
      params: {
        "168": { text: effectivePrompt },
        "158": { noise_seed: Math.floor(Math.random() * 1000000) },
        "278": { image: names[0] || "" },
        "270": { image: names[1] || "" },
        "292": { image: names[2] || "" },
        "313": { value: Boolean(names[1]) },
        "314": { value: Boolean(names[2]) },
        editModel,
        editUpscale,
        editUpscaleRes,
      },
      client_id: newCanvasClientId(),
    });
    const result = await waitForComfyTask(task.task_id);
    const base = result.images ?? [];
    if (!base.length) throw new Error("ComfyUI 编辑未返回图片");
    images = editUpscale ? await runComfyUpscale(base[0], editUpscaleRes) : base;
  } else {
    const workflowJson = workflow || "Z-Image.json";
    const task = await createCanvasComfyTask({
      prompt: effectivePrompt,
      width,
      height,
      workflow_json: workflowJson,
      type: "workflow-custom",
      params: { mode, ...(data.comfyParams as Record<string, unknown> | undefined) },
      client_id: newCanvasClientId(),
    });
    const result = await waitForComfyTask(task.task_id);
    images = result.images ?? [];
  }

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
      ? await submitRunningHubWorkflow({
          workflowId,
          nodeInfoList,
          useWallet: String(data.rhPayment ?? "") === "wallet",
        })
      : await submitRunningHub({
          webappId,
          nodeInfoList,
          instanceType: String(data.instanceType ?? ""),
          useWallet: String(data.rhPayment ?? "") === "wallet",
        });
  if (!submit.taskId) throw new Error("未返回 taskId");
  const result = await waitForRhTask(submit.taskId);
  const urls = result.urls ?? [];
  if (urls.length) writeUrls(runtime, id, urls);
  runtime.updateNodeData(id, { running: false, runStatus: "succeeded" });
  runtime.appendLog({ nodeId: id, nodeType: "rh", status: "succeeded", message: "RunningHub 完成" });
}

export async function runLtxDirectorNode(node: Node, runtime: RunNodeRuntime): Promise<void> {
  const id = node.id;
  const data = nodeData(node);
  const { sources } = resolvePayload(id, runtime);
  const upstreamPrompt = sources.map((s) => s.prompt).filter(Boolean).join("\n\n");
  const globalPrompt = [String(data.globalPrompt ?? ""), upstreamPrompt].filter(Boolean).join("\n\n").trim();
  const segments = ltxTimelineSegments(node);

  if (!ltxHasRunnableContent(node, sources, globalPrompt)) {
    throw new Error("请连接提示词、图片或配置时间轴片段");
  }
  if (segments.some((s) => s.type === "image" && !s.imageFile && !s.imageB64)) {
    throw new Error("LTX 图片段缺少参考图");
  }

  runtime.updateNodeData(id, { running: true, runStatus: "running", runError: "" });
  runtime.appendLog({ nodeId: id, nodeType: "ltxDirector", status: "running", message: "LTX Director 运行中" });

  try {
    const directorInputs = ltxDirectorBuildTimelinePayload(node, globalPrompt);
    for (const seg of segments) {
      if (seg.type === "image" && !seg.imageFile && seg.imageB64) {
        const url = String(seg.imageB64);
        const fullUrl = url.startsWith("http")
          ? url
          : `${window.location.origin}${url.startsWith("/") ? url : `/${url}`}`;
        seg.imageFile = await uploadUrlToComfy(fullUrl);
      }
    }

    const params = {
      [LTX_DIRECTOR_WF_NODE]: directorInputs,
      [LTX_DIRECTOR_SEED_NODE]: { noise_seed: Number(data.noiseSeed ?? 12) },
    };

    const task = await createCanvasComfyTask({
      prompt: globalPrompt || segments.map((s) => s.prompt).join(" | "),
      workflow_json: LTX_DIRECTOR_WORKFLOW,
      params,
      type: "ltx-director",
      client_id: newCanvasClientId(),
    });
    const result = await waitForComfyTask(task.task_id);
    const images = result.images ?? [];
    if (!images.length) throw new Error("LTX 没有返回产物");
    writeUrls(runtime, id, images, "video");
    runtime.updateNodeData(id, {
      running: false,
      runStatus: "succeeded",
      ltxTimelineData: directorInputs.timeline_data,
    });
    runtime.appendLog({
      nodeId: id,
      nodeType: "ltxDirector",
      status: "succeeded",
      message: `LTX 完成 ${images.length} 个产物`,
    });
  } catch (err) {
    runtime.updateNodeData(id, { running: false, runStatus: "failed" });
    throw err;
  }
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

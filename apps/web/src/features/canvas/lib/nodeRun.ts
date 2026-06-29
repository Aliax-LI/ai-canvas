import {
  pollCanvasComfyTask,
  pollCanvasImageTask,
  pollRunningHubTask,
} from "../api";

export async function waitForImageTask(taskId: string): Promise<string[]> {
  for (let i = 0; i < 60; i++) {
    const result = await pollCanvasImageTask(taskId);
    if (result.status === "succeeded") return result.result?.images ?? [];
    if (result.status === "failed") throw new Error(result.error ?? "生成失败");
    await new Promise((r) => setTimeout(r, 1600));
  }
  throw new Error("生成超时");
}

export async function waitForComfyTask(taskId: string): Promise<{ images?: string[] }> {
  for (let i = 0; i < 60; i++) {
    const result = await pollCanvasComfyTask(taskId);
    if (result.status === "succeeded") return result.result ?? {};
    if (result.status === "failed") throw new Error(result.error ?? "ComfyUI 生成失败");
    await new Promise((r) => setTimeout(r, 1600));
  }
  throw new Error("ComfyUI 生成超时");
}

export async function waitForRhTask(taskId: string): Promise<{ urls?: string[] }> {
  for (let i = 0; i < 120; i++) {
    const result = await pollRunningHubTask(taskId);
    const status = result.data?.status;
    if (status === "SUCCESS") return result.data ?? {};
    if (status === "FAILED") throw new Error("RunningHub 任务失败");
    await new Promise((r) => setTimeout(r, 2500));
  }
  throw new Error("RunningHub 任务超时");
}

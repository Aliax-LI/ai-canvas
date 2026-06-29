import { api } from "@/lib/api/client";
import type {
  ApiProvider,
  SaveProviderPayload,
  TestConnectionPayload,
  WorkflowConfig,
  WorkflowDetail,
  WorkflowSummary,
} from "./types";

export async function fetchProviders(): Promise<ApiProvider[]> {
  const data = await api.get<{ providers: ApiProvider[] }>("/providers");
  return data.providers;
}

export async function saveProviders(payload: SaveProviderPayload[]): Promise<ApiProvider[]> {
  const data = await api.put<{ providers: ApiProvider[] }>("/providers", payload);
  return data.providers;
}

export async function testProviderConnection(payload: TestConnectionPayload): Promise<unknown> {
  return api.post("/providers/test-connection", payload);
}

export async function fetchUpstreamModels(payload: TestConnectionPayload): Promise<unknown> {
  return api.post("/providers/fetch-models", payload);
}

export async function fetchComfyInstances(): Promise<string[]> {
  const data = await api.get<{ instances: string[] }>("/comfyui/instances");
  return data.instances;
}

export async function saveComfyInstances(instances: string[]): Promise<string[]> {
  const data = await api.put<{ instances: string[] }>("/comfyui/instances", { instances });
  return data.instances;
}

export async function fetchWorkflows(): Promise<WorkflowSummary[]> {
  const data = await api.get<{ workflows: WorkflowSummary[] }>("/workflows");
  return data.workflows;
}

export async function fetchWorkflow(name: string): Promise<WorkflowDetail> {
  return api.get<WorkflowDetail>(`/workflows/${encodeURIComponent(name)}`);
}

export async function saveWorkflowConfig(name: string, config: WorkflowConfig): Promise<unknown> {
  return api.put(`/workflows/${encodeURIComponent(name)}/config`, config);
}

export async function deleteWorkflow(name: string): Promise<unknown> {
  return api.delete(`/workflows/${encodeURIComponent(name)}`);
}

export async function uploadWorkflow(name: string, workflow: Record<string, unknown>): Promise<unknown> {
  return api.post("/workflows", { name, workflow });
}

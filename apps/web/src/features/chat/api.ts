import { api } from "@/lib/api/client";
import { getApiBase } from "@/lib/api/base";
import type { AiConfig, ConversationDetail, ConversationSummary } from "./types";

export async function fetchConversations(): Promise<ConversationSummary[]> {
  const data = await api.get<{ conversations: ConversationSummary[] }>("/conversations");
  return data.conversations;
}

export async function fetchConversation(id: string): Promise<ConversationDetail> {
  const data = await api.get<{ conversation: ConversationDetail }>(
    `/conversations/${encodeURIComponent(id)}`,
  );
  return data.conversation;
}

export async function createConversation(title = "新对话"): Promise<ConversationDetail> {
  const data = await api.post<{ conversation: ConversationDetail }>("/conversations", { title });
  return data.conversation;
}

export async function deleteConversation(id: string): Promise<void> {
  await api.delete(`/conversations/${encodeURIComponent(id)}`);
}

export async function fetchAiConfig(): Promise<AiConfig> {
  return api.get<AiConfig>("/config");
}

export interface StreamChatOptions {
  conversationId: string;
  message: string;
  provider: string;
  model: string;
  systemPrompt?: string;
  onDelta: (text: string) => void;
  onDone: (conversationId: string) => void;
  onError: (error: Error) => void;
  signal?: AbortSignal;
}

export async function streamChat(options: StreamChatOptions): Promise<void> {
  const response = await fetch(`${getApiBase()}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      conversation_id: options.conversationId,
      message: options.message,
      provider: options.provider,
      model: options.model,
      system_prompt: options.systemPrompt ?? "",
      mode: "chat",
    }),
    signal: options.signal,
  });

  if (!response.ok) {
    const text = await response.text();
    let detail = `请求失败 (${response.status})`;
    try {
      const parsed = JSON.parse(text) as { detail?: unknown };
      if (typeof parsed.detail === "string") detail = parsed.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const body = (await response.json()) as { conversation?: { id: string }; message?: { content: string } };
    if (body.message?.content) options.onDelta(body.message.content);
    options.onDone(body.conversation?.id ?? options.conversationId);
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("无法读取流式响应");

  const decoder = new TextDecoder();
  let buffer = "";
  let resolvedConversationId = options.conversationId;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue;
      const payload = trimmed.slice(5).trim();
      if (!payload || payload === "[DONE]") continue;
      try {
        const json = JSON.parse(payload) as {
          conversation_id?: string;
          choices?: { delta?: { content?: string } }[];
        };
        if (json.conversation_id) resolvedConversationId = json.conversation_id;
        const delta = json.choices?.[0]?.delta?.content;
        if (delta) options.onDelta(delta);
      } catch {
        /* ignore malformed chunks */
      }
    }
  }

  options.onDone(resolvedConversationId);
}

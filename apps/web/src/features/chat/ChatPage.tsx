import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, MessageSquarePlus, Send, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  createConversation,
  deleteConversation,
  fetchAiConfig,
  fetchConversation,
  fetchConversations,
  streamChat,
} from "./api";
import type { ChatMessage } from "./types";

export function ChatPage() {
  const queryClient = useQueryClient();
  const [activeId, setActiveId] = useState("");
  const [draft, setDraft] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [liveMessages, setLiveMessages] = useState<ChatMessage[]>([]);
  const [streamBuffer, setStreamBuffer] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const configQuery = useQuery({ queryKey: ["ai-config"], queryFn: fetchAiConfig });
  const listQuery = useQuery({ queryKey: ["conversations"], queryFn: fetchConversations });
  const detailQuery = useQuery({
    queryKey: ["conversation", activeId],
    queryFn: () => fetchConversation(activeId),
    enabled: Boolean(activeId),
  });

  const conversations = listQuery.data ?? [];
  const config = configQuery.data;

  const provider = useMemo(() => {
    const providers = config?.api_providers ?? [];
    return providers.find((p) => p.primary) ?? providers[0];
  }, [config]);

  const [providerId, setProviderId] = useState("");
  const [model, setModel] = useState("");

  useEffect(() => {
    if (provider && !providerId) {
      setProviderId(provider.id);
      setModel(provider.chat_models?.[0] ?? config?.chat_models?.[0] ?? "");
    }
  }, [provider, providerId, config]);

  useEffect(() => {
    if (!activeId && conversations[0]?.id) {
      setActiveId(conversations[0].id);
    }
  }, [conversations, activeId]);

  useEffect(() => {
    if (detailQuery.data?.messages) {
      setLiveMessages(detailQuery.data.messages.filter((m) => m.role !== "system"));
      setStreamBuffer("");
    }
  }, [detailQuery.data]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [liveMessages, streamBuffer]);

  const newChatMutation = useMutation({
    mutationFn: () => createConversation(),
    onSuccess: (conv) => {
      setActiveId(conv.id);
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  const deleteChatMutation = useMutation({
    mutationFn: deleteConversation,
    onSuccess: () => {
      setActiveId("");
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  const handleSend = async () => {
    const text = draft.trim();
    if (!text || streaming) return;
    if (!providerId || !model) {
      toast.error("请先在 API 设置中配置对话模型");
      return;
    }

    let conversationId = activeId;
    if (!conversationId) {
      const created = await createConversation(text.slice(0, 40));
      conversationId = created.id;
      setActiveId(conversationId);
    }

    const userMsg: ChatMessage = { role: "user", content: text };
    setLiveMessages((prev) => [...prev, userMsg]);
    setDraft("");
    setStreaming(true);
    setStreamBuffer("");

    abortRef.current?.abort();
    abortRef.current = new AbortController();

    try {
      await streamChat({
        conversationId,
        message: text,
        provider: providerId,
        model,
        onDelta: (chunk) => setStreamBuffer((prev) => prev + chunk),
        onDone: (id) => {
          setActiveId(id);
          setStreaming(false);
          setStreamBuffer("");
          void queryClient.invalidateQueries({ queryKey: ["conversations"] });
          void queryClient.invalidateQueries({ queryKey: ["conversation", id] });
        },
        onError: (err) => toast.error(err.message),
        signal: abortRef.current.signal,
      });
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        toast.error(err instanceof Error ? err.message : "发送失败");
      }
      setStreaming(false);
      setStreamBuffer("");
    }
  };

  const displayMessages = streamBuffer
    ? [...liveMessages, { role: "assistant" as const, content: streamBuffer }]
    : liveMessages;

  return (
    <div className="flex h-[calc(100vh-8rem)] min-h-[560px] overflow-hidden rounded-lg border border-border bg-card" data-testid="chat-page">
      <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-muted/30">
        <div className="flex items-center justify-between border-b border-border p-3">
          <span className="text-sm font-medium">对话</span>
          <Button type="button" size="icon" variant="ghost" onClick={() => newChatMutation.mutate()}>
            <MessageSquarePlus className="size-4" />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {conversations.map((conv) => (
            <div key={conv.id} className="group relative mb-1">
              <button
                type="button"
                onClick={() => setActiveId(conv.id)}
                className={`w-full rounded-md px-3 py-2 text-left text-sm transition-colors ${
                  activeId === conv.id ? "bg-accent font-medium" : "hover:bg-muted"
                }`}
              >
                <div className="truncate">{conv.title}</div>
                <div className="truncate text-xs text-muted-foreground">{conv.last_message || "新对话"}</div>
              </button>
              <button
                type="button"
                className="absolute right-1 top-1 hidden rounded p-1 text-muted-foreground hover:bg-muted group-hover:block"
                onClick={() => deleteChatMutation.mutate(conv.id)}
              >
                <Trash2 className="size-3.5" />
              </button>
            </div>
          ))}
        </div>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center gap-3 border-b border-border px-4 py-3">
          <h1 className="text-base font-semibold">GPT 对话</h1>
          <select
            className="h-8 rounded-md border border-input bg-background px-2 text-xs"
            value={providerId}
            onChange={(e) => {
              setProviderId(e.target.value);
              const p = config?.api_providers.find((x) => x.id === e.target.value);
              setModel(p?.chat_models?.[0] ?? config?.chat_models?.[0] ?? "");
            }}
          >
            {(config?.api_providers ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name || p.id}
              </option>
            ))}
          </select>
          <select
            className="h-8 min-w-[140px] rounded-md border border-input bg-background px-2 text-xs"
            value={model}
            onChange={(e) => setModel(e.target.value)}
          >
            {(config?.api_providers.find((p) => p.id === providerId)?.chat_models ??
              config?.chat_models ??
              []
            ).map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-6">
          {!displayMessages.length ? (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-muted-foreground">
              <MessageSquarePlus className="size-10 opacity-40" />
              <p className="text-sm">开始一段新对话</p>
            </div>
          ) : (
            <div className="mx-auto flex max-w-3xl flex-col gap-4">
              {displayMessages.map((msg, index) => (
                <div
                  key={`${msg.id ?? index}-${msg.role}`}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "border border-border bg-background"
                    } ${streaming && index === displayMessages.length - 1 && msg.role === "assistant" ? "animate-pulse" : ""}`}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <div className="border-t border-border p-4">
          <div className="mx-auto flex max-w-3xl gap-2">
            <Textarea
              rows={2}
              placeholder="输入消息…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void handleSend();
                }
              }}
              disabled={streaming}
            />
            <Button type="button" onClick={() => void handleSend()} disabled={streaming || !draft.trim()}>
              {streaming ? <Loader2 className="animate-spin" /> : <Send />}
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  last_message?: string;
}

export interface ChatMessage {
  id?: string;
  role: "user" | "assistant" | "system";
  content: string;
  type?: string;
  created_at?: number;
  attachments?: unknown[];
  mode?: string;
}

export interface ConversationDetail {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  messages: ChatMessage[];
}

export interface AiConfig {
  chat_models: string[];
  image_models: string[];
  video_models: string[];
  api_providers: { id: string; name: string; primary?: boolean; chat_models?: string[]; image_models?: string[] }[];
}

export interface HistoryItem {
  timestamp: number;
  prompt?: string;
  images: string[];
  type?: string;
  params?: Record<string, unknown>;
}

export interface GenerateResult {
  images?: string[];
  url?: string;
  timestamp?: number;
  error?: string;
  task_id?: string;
  status?: string;
}

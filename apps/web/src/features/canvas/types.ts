export interface CanvasRecord {
  id: string;
  title: string;
  icon: string;
  kind: string;
  project: string;
  board_x?: number | null;
  board_y?: number | null;
  pinned?: boolean;
  color?: string;
  created_at: number;
  updated_at: number;
  node_count?: number;
  deleted_at?: number;
}

export interface ProjectRecord {
  id: string;
  name: string;
  order?: number;
}

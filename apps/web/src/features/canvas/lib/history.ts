import type { Edge, Node } from "@xyflow/react";

export const UNDO_MAX = 30;

export interface CanvasSnapshot {
  nodes: Node[];
  edges: Edge[];
}

export function cloneSnapshot(nodes: Node[], edges: Edge[]): CanvasSnapshot {
  return {
    nodes: structuredClone(nodes),
    edges: structuredClone(edges),
  };
}

export interface ClipboardPayload {
  nodes: Node[];
  edges: Edge[];
}

const PASTE_OFFSET = 40;

export function cloneNodesForPaste(
  clip: ClipboardPayload,
  center: { x: number; y: number },
  newNodeId: (prefix: string) => string,
  newEdgeId: () => string,
): { nodes: Node[]; edges: Edge[] } {
  const xs = clip.nodes.map((n) => n.position.x);
  const ys = clip.nodes.map((n) => n.position.y);
  const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
  const cy = (Math.min(...ys) + Math.max(...ys)) / 2;
  const dx = center.x - cx + PASTE_OFFSET;
  const dy = center.y - cy + PASTE_OFFSET;

  const idMap = new Map<string, string>();
  const copies: Node[] = clip.nodes.map((n) => {
    const prefix = String(n.data?.nodeType ?? n.type ?? "node").slice(0, 6);
    const newId = newNodeId(prefix);
    idMap.set(n.id, newId);
    return {
      ...structuredClone(n),
      id: newId,
      position: { x: n.position.x + dx, y: n.position.y + dy },
      selected: true,
      data: {
        ...(n.data as Record<string, unknown>),
        running: false,
        runStatus: "",
        runError: "",
        _cascadeIdx: "",
      },
    };
  });

  for (const copy of copies) {
    const data = copy.data as Record<string, unknown>;
    const type = String(data.nodeType ?? copy.type ?? "");
    if ((type === "group" || type === "promptGroup") && Array.isArray(data.items)) {
      copy.data = {
        ...data,
        items: (data.items as string[]).map((itemId) => idMap.get(itemId) ?? itemId),
      };
    }
  }

  const newEdges = clip.edges
    .map((e) => {
      const from = idMap.get(e.source);
      const to = idMap.get(e.target);
      if (!from || !to) return null;
      return {
        ...structuredClone(e),
        id: newEdgeId(),
        source: from,
        target: to,
      };
    })
    .filter((e): e is Edge => Boolean(e));

  return { nodes: copies, edges: newEdges };
}

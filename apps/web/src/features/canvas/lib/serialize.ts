import type { Edge, Node, Viewport } from "@xyflow/react";
import type { CanvasViewport, LegacyCanvasNode, LegacyConnection } from "../types";

/** 上游 JSON → @xyflow/react */
export function legacyNodesToFlow(nodes: LegacyCanvasNode[]): Node[] {
  return nodes.map((n) => {
    const { id, type, x, y, w, h, ...rest } = n;
    const defW = typeof w === "number" ? w : undefined;
    const defH = typeof h === "number" ? h : undefined;
    return {
      id,
      type,
      position: { x: Number(x) || 0, y: Number(y) || 0 },
      data: { ...rest, nodeType: type },
      ...(defW || defH
        ? { style: { width: defW, height: defH, minWidth: 200 } }
        : { style: { minWidth: 200 } }),
    };
  });
}

export function legacyConnectionsToFlow(connections: LegacyConnection[]): Edge[] {
  return connections.map((c) => ({
    id: c.id,
    source: c.from,
    target: c.to,
    type: "default",
  }));
}

export function flowNodesToLegacy(nodes: Node[]): LegacyCanvasNode[] {
  return nodes.map((n) => {
    const data = { ...(n.data as Record<string, unknown>) };
    delete data.nodeType;
    const w = n.style?.width;
    const h = n.style?.height;
    return {
      id: n.id,
      type: n.type ?? "image",
      x: n.position.x,
      y: n.position.y,
      ...(typeof w === "number" ? { w } : {}),
      ...(typeof h === "number" ? { h } : {}),
      ...data,
    };
  });
}

export function flowEdgesToLegacy(edges: Edge[]): LegacyConnection[] {
  return edges.map((e) => ({
    id: e.id,
    from: e.source,
    to: e.target,
  }));
}

export function legacyViewportToFlow(viewport: CanvasViewport): Viewport {
  return {
    x: Number(viewport.x) || 0,
    y: Number(viewport.y) || 0,
    zoom: Number(viewport.scale) || 1,
  };
}

export function flowViewportToLegacy(viewport: Viewport): CanvasViewport {
  return {
    x: viewport.x,
    y: viewport.y,
    scale: viewport.zoom,
  };
}

export function newConnectionId(): string {
  return `c_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

export function newNodeId(prefix: string): string {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

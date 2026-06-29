import type { Edge, Node } from "@xyflow/react";
import { CANVAS_GENERATOR_TYPES } from "./graph";
import { runNodeByType, type RunNodeRuntime } from "./runNode";

export const CASCADE_RUN_TYPES = [
  "generator",
  "msgen",
  "comfy",
  "ltxDirector",
  "llm",
  "video",
  "rh",
] as const;

function nodeType(node: Node): string {
  return String(node.data?.nodeType ?? node.type ?? "");
}

function findNode(nodes: Node[], id: string): Node | undefined {
  return nodes.find((n) => n.id === id);
}

function isCascadeRunType(type: string): boolean {
  return (CASCADE_RUN_TYPES as readonly string[]).includes(type);
}

function isTerminalGenerator(genId: string, nodes: Node[], edges: Edge[]): boolean {
  return !edges.some((e) => {
    if (e.source !== genId) return false;
    const target = findNode(nodes, e.target);
    if (!target) return false;
    const t = nodeType(target);
    return isCascadeRunType(t) || t === "output";
  });
}

/** 拓扑排序上游 generator 链（对齐上游 computeCascadeOrder） */
export function computeCascadeOrder(targetId: string, nodes: Node[], edges: Edge[]): string[] {
  const visited = new Set<string>();
  const order: string[] = [];

  function dfs(id: string) {
    if (visited.has(id)) return;
    visited.add(id);
    const node = findNode(nodes, id);
    if (!node) return;

    for (const edge of edges.filter((e) => e.target === id)) {
      const from = findNode(nodes, edge.source);
      if (!from) continue;
      const fromType = nodeType(from);
      if (isCascadeRunType(fromType)) {
        dfs(from.id);
      } else if (fromType === "output") {
        for (const upEdge of edges.filter((e) => e.target === from.id)) {
          const upstream = findNode(nodes, upEdge.source);
          if (upstream && isCascadeRunType(nodeType(upstream))) {
            dfs(upstream.id);
          }
        }
      }
    }

    if (isCascadeRunType(nodeType(node))) {
      order.push(id);
    }
  }

  dfs(targetId);
  return order;
}

function upstreamNodeIds(targetId: string, _nodes: Node[], edges: Edge[]): Set<string> {
  const found = new Set<string>();
  const walk = (id: string) => {
    for (const edge of edges.filter((e) => e.target === id)) {
      if (found.has(edge.source)) continue;
      found.add(edge.source);
      walk(edge.source);
    }
  };
  walk(targetId);
  return found;
}

export interface ResolvedCascadeLoop {
  node: Node;
  count: number;
  mode: "serial" | "parallel";
}

/** 找关联 loop 节点（对齐上游 resolveCascadeLoop） */
export function resolveCascadeLoop(
  targetId: string,
  nodes: Node[],
  edges: Edge[],
): ResolvedCascadeLoop | null {
  const upstream = upstreamNodeIds(targetId, nodes, edges);
  const loops = nodes.filter((n) => nodeType(n) === "loop" && upstream.has(n.id));
  if (!loops.length) return null;
  const loop = loops[loops.length - 1];
  const data = (loop.data ?? {}) as Record<string, unknown>;
  const count = Math.max(1, Math.min(100, Number(data.count ?? 1) || 1));
  const mode = data.mode === "parallel" ? "parallel" : "serial";
  return { node: loop, count, mode };
}

/** 找 loop 下游级联目标 generator */
export function findLoopCascadeTarget(loopId: string, nodes: Node[], edges: Edge[]): string | null {
  const seen = new Set<string>();
  const candidates: { id: string; depth: number; terminal: boolean }[] = [];

  const walk = (id: string, depth = 0) => {
    if (seen.has(id)) return;
    seen.add(id);
    for (const edge of edges.filter((e) => e.source === id)) {
      const next = findNode(nodes, edge.target);
      if (!next) continue;
      const t = nodeType(next);
      if (isCascadeRunType(t)) {
        candidates.push({
          id: next.id,
          depth: depth + 1,
          terminal: isTerminalGenerator(next.id, nodes, edges),
        });
      }
      walk(next.id, depth + 1);
    }
  };

  walk(loopId);
  const terminal = candidates.filter((c) => c.terminal).sort((a, b) => b.depth - a.depth)[0];
  const picked = terminal ?? candidates.sort((a, b) => b.depth - a.depth)[0];
  return picked?.id ?? null;
}

export interface CascadeRuntime extends RunNodeRuntime {}

function loopStart(node: Node): number {
  const data = (node.data ?? {}) as Record<string, unknown>;
  return Math.max(1, Number(data.loopStart ?? 1) || 1);
}

function loopBatchSize(node: Node): number {
  const data = (node.data ?? {}) as Record<string, unknown>;
  if (!data.imageInput) return 1;
  return Math.max(1, Math.min(100, Number(data.imageBatchSize ?? 1) || 1));
}

/** 串行执行级联（serial loop 模式） */
export async function runNodeCascade(targetId: string, runtime: CascadeRuntime): Promise<void> {
  const nodes = runtime.getNodes();
  const edges = runtime.getEdges();
  const target = findNode(nodes, targetId);
  if (!target) throw new Error("节点不存在");

  const order = computeCascadeOrder(targetId, nodes, edges);
  if (!order.length) throw new Error("没有可运行的生成节点");

  const loop = resolveCascadeLoop(targetId, nodes, edges);
  const totalRounds = loop?.count ?? 1;
  const startIdx = loop ? loopStart(loop.node) : 1;
  const batchSize = loop ? loopBatchSize(loop.node) : 1;
  const endIdx = startIdx + (totalRounds - 1) * batchSize;

  for (const id of order) {
    runtime.updateNodeData(id, { generatedOutputs: [] });
  }

  for (let round = 1; round <= totalRounds; round++) {
    const loopIndex = startIdx + (round - 1) * batchSize;
    const loopCtx = loop
      ? { index: loopIndex, total: endIdx, nodeId: loop.node.id }
      : undefined;

    for (let i = 0; i < order.length; i++) {
      const id = order[i];
      const idxLabel = `${i + 1}/${order.length}${totalRounds > 1 ? ` · ${loopIndex}/${endIdx}` : ""}`;

      runtime.updateNodeData(id, {
        runStatus: "queued",
        runError: "",
        _cascadeIdx: idxLabel,
      });

      runtime.updateNodeData(id, { runStatus: "running", _cascadeIdx: idxLabel });

      try {
        const node = runtime.getNodes().find((n) => n.id === id);
        if (!node) continue;
        await runNodeByType(node, { ...runtime, loopCtx, cascadeTargetId: targetId });
        runtime.updateNodeData(id, { runStatus: "done", running: false, _cascadeIdx: idxLabel });
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        const roundPrefix = totalRounds > 1 ? `第 ${round}/${totalRounds} 轮: ` : "";
        runtime.updateNodeData(id, {
          runStatus: "failed",
          runError: `${roundPrefix}${msg}`,
          running: false,
          _cascadeFailed: true,
        });
        for (let j = i + 1; j < order.length; j++) {
          runtime.updateNodeData(order[j], { runStatus: "", _cascadeIdx: "" });
        }
        throw err;
      }
    }
  }

  for (const id of order) {
    runtime.updateNodeData(id, { _cascadeIdx: "", runStatus: "succeeded" });
  }
}

export function canCascadeFromNode(nodeId: string, nodes: Node[], edges: Edge[]): boolean {
  return resolveCascadeTargetId(nodeId, nodes, edges) !== null;
}

export function resolveCascadeTargetId(
  nodeId: string,
  nodes: Node[],
  edges: Edge[],
): string | null {
  const node = findNode(nodes, nodeId);
  if (!node) return null;
  const type = nodeType(node);
  if (isCascadeRunType(type) || type === "output") return nodeId;
  if (type === "loop") return findLoopCascadeTarget(nodeId, nodes, edges);
  return null;
}

export function isRunnableGeneratorType(type: string): boolean {
  return (CANVAS_GENERATOR_TYPES as readonly string[]).includes(type);
}

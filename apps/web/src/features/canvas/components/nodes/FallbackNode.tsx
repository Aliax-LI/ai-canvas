import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";

export function FallbackNode({ id, data, selected }: CanvasNodeProps) {
  const nodeType = String(data.nodeType ?? "unknown");
  const preview = JSON.stringify(
    Object.fromEntries(Object.entries(data).filter(([k]) => k !== "nodeType")),
    null,
    2,
  );

  return (
    <BaseNodeShell
      type="fallback"
      title={`未知节点 · ${nodeType}`}
      selected={selected}
      className="max-w-[320px]"
      data-testid={`canvas-node-${id}`}
    >
      <div className="nodrag">
        <p className="mb-2 text-xs text-muted-foreground">类型「{nodeType}」尚未迁移，已保留全部 data 字段。</p>
        <pre className="max-h-40 overflow-auto rounded-md bg-muted p-2 text-[10px] leading-relaxed">
          {preview}
        </pre>
      </div>
    </BaseNodeShell>
  );
}

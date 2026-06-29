import type { NodeProps } from "@xyflow/react";
import { Handle, Position } from "@xyflow/react";
import { cn } from "@/lib/utils";

const ACCENT: Record<string, string> = {
  image: "#71717A",
  prompt: "#52525B",
  output: "#18181B",
  group: "#71717A",
  generator: "#2563EB",
  msgen: "#7C3AED",
  comfy: "#EA580C",
  rh: "#0891B2",
  video: "#DB2777",
  llm: "#059669",
  loop: "#CA8A04",
  text: "#52525B",
  ltxDirector: "#9333EA",
  promptGroup: "#52525B",
  fallback: "#A1A1AA",
};

interface BaseNodeShellProps {
  type: string;
  title: string;
  selected?: boolean;
  running?: boolean;
  error?: boolean;
  children: React.ReactNode;
  className?: string;
  "data-testid"?: string;
}

export function BaseNodeShell({
  type,
  title,
  selected,
  running,
  error,
  children,
  className,
  "data-testid": testId,
}: BaseNodeShellProps) {
  const accent = ACCENT[type] ?? "#71717A";

  return (
    <div
      data-testid={testId}
      className={cn(
        "relative min-w-[200px] rounded-lg border bg-canvas-node-bg text-sm shadow-sm",
        selected
          ? "border-2 border-canvas-node-selected shadow-md"
          : "border border-canvas-node-border",
        running && "border-l-[3px] border-l-info",
        error && "border-l-[3px] border-l-destructive",
        className,
      )}
      style={{ borderLeftColor: running || error ? undefined : accent, borderLeftWidth: 3 }}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!size-2.5 !border-2 !border-canvas-port !bg-canvas-node-bg hover:!size-3"
      />
      <div className="border-b border-border px-3 py-2">
        <div className="truncate text-xs font-semibold">{title}</div>
      </div>
      <div className="p-3">{children}</div>
      <Handle
        type="source"
        position={Position.Right}
        className="!size-2.5 !border-2 !border-canvas-port !bg-canvas-node-bg hover:!size-3"
      />
    </div>
  );
}

export type CanvasNodeProps<T = Record<string, unknown>> = NodeProps & {
  data: T & { nodeType?: string };
};

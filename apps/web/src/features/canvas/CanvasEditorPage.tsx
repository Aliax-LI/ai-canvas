import { useParams } from "react-router-dom";

export function CanvasEditorPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <div className="text-center">
      <p className="text-sm text-muted-foreground">无限画布编辑区（@xyflow/react 待接入）</p>
      <p className="mt-2 font-mono text-xs text-muted-foreground">canvas_id: {id}</p>
      <div
        className="mx-auto mt-8 h-64 w-full max-w-2xl rounded-lg border border-dashed border-canvas-node-border bg-canvas-node-bg"
        style={{
          backgroundImage: "radial-gradient(circle, var(--canvas-grid) 1px, transparent 1px)",
          backgroundSize: "20px 20px",
        }}
      />
    </div>
  );
}

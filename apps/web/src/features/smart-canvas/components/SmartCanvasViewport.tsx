import { useCallback, useRef, useState } from "react";
import type { SmartNode, SmartViewport } from "../types";
import { SmartCard } from "./SmartCard";

interface SmartCanvasViewportProps {
  nodes: SmartNode[];
  viewport: SmartViewport;
  selectedId: string;
  onViewportChange: (viewport: SmartViewport) => void;
  onNodesChange: (nodes: SmartNode[]) => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onTextChange: (id: string, text: string) => void;
  onBackgroundClick: () => void;
  onDirty: () => void;
}

export function SmartCanvasViewport({
  nodes,
  viewport,
  selectedId,
  onViewportChange,
  onNodesChange,
  onSelect,
  onDelete,
  onTextChange,
  onBackgroundClick,
  onDirty,
}: SmartCanvasViewportProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const panRef = useRef<{ startX: number; startY: number; originX: number; originY: number } | null>(
    null,
  );
  const dragRef = useRef<{
    nodeId: string;
    startX: number;
    startY: number;
    originX: number;
    originY: number;
  } | null>(null);
  const [isPanning, setIsPanning] = useState(false);

  const clampScale = (value: number) => Math.min(2.5, Math.max(0.25, value));

  const onWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.08 : 0.08;
      onViewportChange({ ...viewport, scale: clampScale(viewport.scale + delta) });
      onDirty();
    },
    [viewport, onViewportChange, onDirty],
  );

  const onPointerDownBackground = (e: React.PointerEvent) => {
    if (e.button !== 0 && e.button !== 1) return;
    panRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      originX: viewport.x,
      originY: viewport.y,
    };
    setIsPanning(true);
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  };

  const onPointerMoveBackground = (e: React.PointerEvent) => {
    if (dragRef.current) {
      const node = nodes.find((n) => n.id === dragRef.current?.nodeId);
      if (!node || !dragRef.current) return;
      const dx = (e.clientX - dragRef.current.startX) / viewport.scale;
      const dy = (e.clientY - dragRef.current.startY) / viewport.scale;
      onNodesChange(
        nodes.map((n) =>
          n.id === node.id
            ? { ...n, x: dragRef.current!.originX + dx, y: dragRef.current!.originY + dy }
            : n,
        ),
      );
      return;
    }
    if (!panRef.current) return;
    const dx = e.clientX - panRef.current.startX;
    const dy = e.clientY - panRef.current.startY;
    onViewportChange({
      ...viewport,
      x: panRef.current.originX + dx,
      y: panRef.current.originY + dy,
    });
  };

  const endPointer = (e: React.PointerEvent) => {
    if (dragRef.current) {
      onDirty();
      dragRef.current = null;
    }
    if (panRef.current) {
      onDirty();
      panRef.current = null;
      setIsPanning(false);
    }
    try {
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
  };

  const onCardPointerDown = (nodeId: string, e: React.PointerEvent) => {
    e.stopPropagation();
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return;
    dragRef.current = {
      nodeId,
      startX: e.clientX,
      startY: e.clientY,
      originX: node.x,
      originY: node.y,
    };
    onSelect(nodeId);
    (containerRef.current as HTMLElement)?.setPointerCapture(e.pointerId);
  };

  return (
    <div
      ref={containerRef}
      data-testid="smart-canvas-viewport"
      className={`relative h-full w-full overflow-hidden bg-canvas-bg ${
        isPanning ? "cursor-grabbing" : "cursor-grab"
      }`}
      style={{
        backgroundImage: "radial-gradient(circle, var(--canvas-grid) 1px, transparent 1px)",
        backgroundSize: `${20 * viewport.scale}px ${20 * viewport.scale}px`,
        backgroundPosition: `${viewport.x}px ${viewport.y}px`,
      }}
      onWheel={onWheel}
      onPointerDown={onPointerDownBackground}
      onPointerMove={onPointerMoveBackground}
      onPointerUp={endPointer}
      onPointerCancel={endPointer}
      onClick={(e) => {
        if (e.target === e.currentTarget) onBackgroundClick();
      }}
    >
      <div
        className="absolute left-0 top-0"
        style={{
          transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.scale})`,
          transformOrigin: "0 0",
        }}
      >
        {nodes.map((node) => (
          <SmartCard
            key={node.id}
            node={node}
            selected={selectedId === node.id}
            scale={1}
            onSelect={onSelect}
            onDelete={onDelete}
            onTextChange={(id, text) => {
              onTextChange(id, text);
              onDirty();
            }}
            onPointerDown={onCardPointerDown}
          />
        ))}
      </div>
    </div>
  );
}

export function viewportCenter(viewport: SmartViewport, container?: DOMRect | null): {
  x: number;
  y: number;
} {
  const w = container?.width ?? 800;
  const h = container?.height ?? 600;
  return {
    x: (w / 2 - viewport.x) / viewport.scale - 120,
    y: (h / 2 - viewport.y) / viewport.scale - 80,
  };
}

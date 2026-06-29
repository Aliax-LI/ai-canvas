import { useCallback, useEffect } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  useReactFlow,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  type OnConnect,
  type Viewport,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { canvasNodeTypes } from "./nodeTypes";
import { newConnectionId } from "../lib/serialize";

const defaultEdgeOptions = {
  style: { stroke: "var(--canvas-edge)", strokeWidth: 2 },
};

interface CanvasFlowInnerProps {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: (nodes: Node[]) => void;
  onEdgesChange: (edges: Edge[]) => void;
  onViewportChange: (viewport: Viewport) => void;
  initialViewport?: Viewport;
  onDirty: () => void;
  onConnect?: OnConnect;
}

function CanvasFlowInner({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onViewportChange,
  initialViewport,
  onDirty,
  onConnect: onConnectProp,
}: CanvasFlowInnerProps) {
  const { setViewport } = useReactFlow();

  useEffect(() => {
    if (initialViewport) {
      void setViewport(initialViewport, { duration: 0 });
    }
  }, [initialViewport, setViewport]);

  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      const hasRemove = changes.some((c) => c.type === "remove");
      onNodesChange(applyNodeChanges(changes, nodes));
      if (changes.some((c) => c.type !== "select")) onDirty();
      if (hasRemove) {
        const removedIds = new Set(
          changes.filter((c) => c.type === "remove").map((c) => c.id),
        );
        if (removedIds.size) {
          onEdgesChange(edges.filter((e) => !removedIds.has(e.source) && !removedIds.has(e.target)));
        }
      }
    },
    [nodes, edges, onNodesChange, onEdgesChange, onDirty],
  );

  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      onEdgesChange(applyEdgeChanges(changes, edges));
      if (changes.length) onDirty();
    },
    [edges, onEdgesChange, onDirty],
  );

  const handleConnect: OnConnect = useCallback(
    (connection: Connection) => {
      if (onConnectProp) {
        onConnectProp(connection);
        return;
      }
      onEdgesChange(
        addEdge(
          {
            ...connection,
            id: newConnectionId(),
            type: "default",
          },
          edges,
        ),
      );
      onDirty();
    },
    [edges, onEdgesChange, onDirty, onConnectProp],
  );

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={canvasNodeTypes}
      onNodesChange={handleNodesChange}
      onEdgesChange={handleEdgesChange}
      onConnect={handleConnect}
      onMoveEnd={(_, viewport) => onViewportChange(viewport)}
      defaultEdgeOptions={defaultEdgeOptions}
      fitView={!initialViewport}
      minZoom={0.1}
      maxZoom={2}
      proOptions={{ hideAttribution: true }}
      className="bg-canvas-bg"
      data-testid="canvas-flow"
      selectionOnDrag
      panOnDrag={[1, 2]}
      selectionKeyCode={null}
      multiSelectionKeyCode="Shift"
      deleteKeyCode={["Backspace", "Delete"]}
    >
      <Background
        variant={BackgroundVariant.Dots}
        gap={20}
        size={1}
        color="var(--canvas-grid)"
      />
      <Controls className="!border-border !bg-card !shadow-md" />
      <MiniMap
        className="!rounded-md !border !border-border !bg-canvas-minimap"
        nodeColor="var(--canvas-node-border)"
        maskColor="rgba(0,0,0,0.08)"
      />
    </ReactFlow>
  );
}

export interface CanvasFlowProps extends CanvasFlowInnerProps {}

export function CanvasFlow(props: CanvasFlowProps) {
  return (
    <ReactFlowProvider>
      <div className="h-full w-full" data-testid="canvas-editor-viewport">
        <CanvasFlowInner {...props} />
      </div>
    </ReactFlowProvider>
  );
}

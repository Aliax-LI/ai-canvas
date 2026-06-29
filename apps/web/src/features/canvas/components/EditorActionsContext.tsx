import { createContext, useContext } from "react";
import type { Edge, Node } from "@xyflow/react";
import type { GeneratorSource, MediaRef, RunPayload } from "../lib/graph";
import type { CanvasLogEntry } from "../lib/runHelpers";

export interface CanvasEditorActions {
  nodes: Node[];
  edges: Edge[];
  updateNodeData: (nodeId: string, patch: Record<string, unknown>) => void;
  scheduleSave: () => void;
  getRunContext: (nodeId: string) => RunPayload;
  appendLog: (entry: Omit<CanvasLogEntry, "id" | "ts"> & { ts?: number }) => void;
  writeOutputImages: (outputNodeId: string, urls: string[]) => void;
}

export type { GeneratorSource, MediaRef, RunPayload, CanvasLogEntry };

const CanvasEditorActionsContext = createContext<CanvasEditorActions | null>(null);

export function CanvasEditorActionsProvider({
  value,
  children,
}: {
  value: CanvasEditorActions;
  children: React.ReactNode;
}) {
  return (
    <CanvasEditorActionsContext.Provider value={value}>{children}</CanvasEditorActionsContext.Provider>
  );
}

export function useCanvasEditorActions(): CanvasEditorActions {
  const ctx = useContext(CanvasEditorActionsContext);
  if (!ctx) throw new Error("useCanvasEditorActions must be used within provider");
  return ctx;
}
